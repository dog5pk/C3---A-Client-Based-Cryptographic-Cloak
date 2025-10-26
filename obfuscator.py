#!/usr/bin/env python3
"""
obfuscator.py - minimal Cactus-style client-side obfuscation proof-of-concept.

This script uses the BCC library to attach a kprobe to the kernel
`tcp_sendmsg()` function in order to record the size of each outgoing
TCP send operation.  It also implements two simple obfuscation
primitives, random segmentation and random padding, in user space.  A
test harness at the bottom of this file exercises the primitives by
fetching a URL from a local server and printing before/after packet
metrics.

Dependencies:

  * Python 3.8+
  * bcc (`sudo apt install python3-bcc` on Ubuntu 22.04)
  * docker (optional, for running nginx; see README)

Because we are running as a normal user, the eBPF program is used for
observability only – it records send sizes but does not modify
packets.  The actual segmentation and padding happens in user space
using Python's socket API.  This architecture follows the design of
Cactus: instrumentation in the kernel combined with a userspace
controller that applies obfuscation decisions.

Usage:

  python3 obfuscator.py baseline
      -> fetches a page from http://localhost:8080 with no obfuscation
         and prints packet sizes/timings.

  python3 obfuscator.py obfuscate
      -> applies random segmentation and padding to the request body
         before sending it; prints packet sizes/timings.

The BPF program runs in the background and prints each send size
observed to standard error.  You can redirect this output to a file
for further analysis.
"""

from __future__ import annotations

import os
import sys
import time
import socket
import random
import threading
from datetime import datetime
from typing import List, Tuple

try:
    from bcc import BPF
except ImportError as e:
    print("Error: bcc library not found. Install it with 'sudo apt install python3-bcc'", file=sys.stderr)
    raise

# eBPF program: attach to tcp_sendmsg and emit the size argument via bpf_trace_printk.
_BPF_PROGRAM = """
#include <uapi/linux/ptrace.h>

int trace_tcp_sendmsg(struct pt_regs *ctx, struct sock *sk, struct msghdr *msg, size_t size) {
    // Emit the size of the send operation to the trace pipe.  arg2 is the size.
    bpf_trace_printk("%d\n", size);
    return 0;
}
"""

def attach_bpf() -> BPF:
    """Compile and attach the eBPF program.  Returns the BPF object."""
    b = BPF(text=_BPF_PROGRAM)
    # Attach kprobe to tcp_sendmsg.  On kernels where the symbol is not
    # available, this will raise an exception.  Check dmesg or /proc/kallsyms
    # for the correct symbol name if this fails.
    b.attach_kprobe(event="tcp_sendmsg", fn_name="trace_tcp_sendmsg")
    return b

def run_bpf_logger(bpf_obj: BPF, stop_event: threading.Event) -> None:
    """
    Continuously read from the BPF trace pipe and print send sizes.
    This runs in a separate thread until stop_event is set.
    """
    while not stop_event.is_set():
        try:
            # read more lines than we need so we don't block often
            (task, pid, cpu, flags, ts, msg) = bpf_obj.trace_fields(timeout=1000)
            # msg is bytes; decode and strip
            print(f"[BPF] send size: {msg.strip().decode()} bytes", file=sys.stderr)
        except ValueError:
            continue
        except KeyboardInterrupt:
            break

def random_segments(data: bytes, min_size: int = 16, max_size: int = 64) -> List[bytes]:
    """Split the data into random segments between min_size and max_size bytes."""
    segments: List[bytes] = []
    pos = 0
    length = len(data)
    while pos < length:
        remaining = length - pos
        seg_len = random.randint(min_size, max_size)
        seg_len = min(seg_len, remaining)
        segments.append(data[pos:pos + seg_len])
        pos += seg_len
    return segments

def random_pad(data: bytes, min_pad: int = 0, max_pad: int = 32) -> bytes:
    """Return data padded with a random number of zero bytes between min_pad and max_pad."""
    pad_len = random.randint(min_pad, max_pad)
    return data + b"\x00" * pad_len

def send_request(segmented: bool, padded: bool) -> Tuple[List[int], List[float]]:
    """
    Send a simple HTTP GET request to localhost:8080 with optional
    segmentation and padding.  Returns a list of packet sizes and the
    list of inter-packet gaps (seconds).
    """
    addr = ("127.0.0.1", 8080)
    # Compose a minimal HTTP GET request.
    request = b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
    # Apply random padding to the entire request if enabled.
    if padded:
        request = random_pad(request)
    # Apply random segmentation if enabled.
    segments = random_segments(request) if segmented else [request]
    pkt_sizes: List[int] = []
    timestamps: List[float] = []
    with socket.create_connection(addr) as sock:
        for i, seg in enumerate(segments):
            # record send timestamp
            before = time.time()
            sock.sendall(seg)
            after = time.time()
            pkt_sizes.append(len(seg))
            timestamps.append(after)
        # Receive response to ensure connection is closed properly
        while True:
            data = sock.recv(4096)
            if not data:
                break
    # Compute inter-packet gaps
    gaps: List[float] = []
    for i in range(1, len(timestamps)):
        gaps.append(timestamps[i] - timestamps[i - 1])
    return pkt_sizes, gaps

def print_metrics(label: str, sizes: List[int], gaps: List[float]) -> None:
    """
    Print basic statistics about packet sizes and inter-packet gaps.
    """
    print(f"--- {label} ---")
    print(f"Packets sent: {len(sizes)}")
    print(f"Sizes: {sizes}")
    if gaps:
        print(f"Inter-packet gaps (s): {[round(g, 6) for g in gaps]}")
    else:
        print("Inter-packet gaps: n/a (single segment)")

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"baseline", "obfuscate"}:
        print("Usage: python3 obfuscator.py [baseline|obfuscate]", file=sys.stderr)
        sys.exit(1)
    mode = sys.argv[1]
    # Attach BPF for monitoring send sizes.
    bpf_obj = attach_bpf()
    stop_event = threading.Event()
    logger_thread = threading.Thread(target=run_bpf_logger, args=(bpf_obj, stop_event), daemon=True)
    logger_thread.start()
    try:
        if mode == "baseline":
            sizes, gaps = send_request(segmented=False, padded=False)
            print_metrics("Baseline", sizes, gaps)
        else:
            sizes, gaps = send_request(segmented=True, padded=True)
            print_metrics("Obfuscated", sizes, gaps)
    finally:
        stop_event.set()
        # give thread time to exit
        logger_thread.join(timeout=1)

if __name__ == "__main__":
    main()
