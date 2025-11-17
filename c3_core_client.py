#!/usr/bin/env python3
"""
c3_core_client.py

C³ Core Obfuscation Client (production-grade baseline).

This client connects to a remote TCP server (e.g. a D-Bridge relay or
C3 demo relay) and sends an HTTP GET request either in:
  - baseline mode: single unmodified send
  - obfuscate mode: segmented, padded, and jittered according to a
    C3 policy file.

The client is designed to be policy-driven. A JSON policy file can be
supplied at runtime to control segmentation, padding, and timing
parameters.

Example policy (c3_policy.json):

{
  "version": "c3-policy-v1",
  "profile_name": "lab-default",
  "segment": { "min": 16, "max": 64 },
  "padding": { "max": 16 },
  "timing": { "max_delay_ms": 5 },
  "meta": {
    "source": "manual",
    "stealth_confidence": 0.0,
    "last_updated": "2025-11-16T00:00:00Z"
  }
}

If no policy is provided, sane defaults are used.

This module is written with production hardening in mind:
  - explicit validation of policy values
  - clear error messages
  - logging with timestamps and levels
  - graceful shutdown on errors
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List


DEFAULT_MIN_SEG = 16
DEFAULT_MAX_SEG = 64
DEFAULT_MAX_PAD = 16
DEFAULT_MAX_DELAY_MS = 5.0

LOGGER = logging.getLogger("c3_core_client")


@dataclass
class SegmentConfig:
    min: int
    max: int


@dataclass
class PaddingConfig:
    max: int


@dataclass
class TimingConfig:
    max_delay_ms: float


@dataclass
class C3Policy:
    version: str
    profile_name: str
    segment: SegmentConfig
    padding: PaddingConfig
    timing: TimingConfig

    @classmethod
    def from_dict(cls, data: dict) -> "C3Policy":
        """
        Construct C3Policy from a dictionary, applying validation and defaults.

        Raises ValueError if the policy is structurally invalid.
        """
        version = str(data.get("version", "c3-policy-v1"))
        profile_name = str(data.get("profile_name", "default"))

        seg = data.get("segment", {}) or {}
        pad = data.get("padding", {}) or {}
        tim = data.get("timing", {}) or {}

        min_seg = int(seg.get("min", DEFAULT_MIN_SEG))
        max_seg = int(seg.get("max", DEFAULT_MAX_SEG))
        max_pad = int(pad.get("max", DEFAULT_MAX_PAD))
        max_delay_ms = float(tim.get("max_delay_ms", DEFAULT_MAX_DELAY_MS))

        errors = []

        if min_seg <= 0:
            errors.append("segment.min must be > 0")
        if max_seg < min_seg:
            errors.append("segment.max must be >= segment.min")
        if max_pad < 0:
            errors.append("padding.max must be >= 0")
        if max_delay_ms < 0:
            errors.append("timing.max_delay_ms must be >= 0")

        if errors:
            raise ValueError("Invalid policy: " + "; ".join(errors))

        return cls(
            version=version,
            profile_name=profile_name,
            segment=SegmentConfig(min=min_seg, max=max_seg),
            padding=PaddingConfig(max=max_pad),
            timing=TimingConfig(max_delay_ms=max_delay_ms),
        )


def load_policy(path: Optional[str]) -> C3Policy:
    """
    Load a C3 policy from a JSON file, or return a default policy
    if no path is provided.

    Any errors in reading/parsing the policy file are treated as fatal.
    """
    if path is None:
        LOGGER.info("No policy file provided; using default built-in policy")
        return C3Policy.from_dict({})

    policy_path = Path(path)
    if not policy_path.is_file():
        raise FileNotFoundError(f"Policy file not found: {policy_path}")

    try:
        with policy_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse policy JSON: {e}") from e

    policy = C3Policy.from_dict(data)
    LOGGER.info(
        "Loaded policy '%s' (version=%s) from %s",
        policy.profile_name,
        policy.version,
        policy_path,
    )
    LOGGER.debug(
        "Policy details: segment=%s padding=%s timing=%s",
        policy.segment,
        policy.padding,
        policy.timing,
    )
    return policy


def send_baseline(host: str, port: int, path: str = "/", count: int = 1) -> None:
    """
    Send count HTTP GET requests in baseline mode: single send per request.
    """
    LOGGER.info("Sending %d baseline request(s) to %s:%d%s", count, host, port, path)
    request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    payload = request.encode("utf-8")

    for i in range(count):
        LOGGER.debug("Baseline request %d: opening connection", i + 1)
        with socket.create_connection((host, port), timeout=10) as sock:
            sock.sendall(payload)
            _drain_response(sock)
        LOGGER.debug("Baseline request %d: completed", i + 1)


def send_obfuscated(
    host: str,
    port: int,
    policy: C3Policy,
    path: str = "/",
    count: int = 1,
    rng_seed: Optional[int] = None,
) -> None:
    """
    Send count HTTP GET requests using obfuscation defined by policy.

    Each request is:
      - split into random segments between policy.segment.min and .max
      - each segment padded with up to policy.padding.max bytes
      - sent with random jitter between 0 and policy.timing.max_delay_ms
    """
    LOGGER.info(
        "Sending %d obfuscated request(s) to %s:%d%s using profile '%s'",
        count,
        host,
        port,
        path,
        policy.profile_name,
    )

    if rng_seed is not None:
        LOGGER.debug("Seeding RNG with %d", rng_seed)
        rng = random.Random(rng_seed)
    else:
        rng = random.Random()

    base_request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    base_payload = base_request.encode("utf-8")

    for i in range(count):
        LOGGER.debug("Obfuscated request %d: opening connection", i + 1)
        with socket.create_connection((host, port), timeout=10) as sock:
            segments = _build_segments(base_payload, policy, rng)
            LOGGER.debug(
                "Obfuscated request %d: sending %d segments", i + 1, len(segments)
            )
            _send_segments(sock, segments, policy, rng)
            _drain_response(sock)
        LOGGER.debug("Obfuscated request %d: completed", i + 1)


def _build_segments(
    payload: bytes,
    policy: C3Policy,
    rng: random.Random,
) -> List[bytes]:
    """
    Split payload into random segments and apply padding per segment.
    """
    segments: List[bytes] = []
    pos = 0
    length = len(payload)

    while pos < length:
        remaining = length - pos
        seg_len = rng.randint(policy.segment.min, policy.segment.max)
        seg_len = min(seg_len, remaining)
        seg = payload[pos : pos + seg_len]
        pad_len = 0
        if policy.padding.max > 0:
            pad_len = rng.randint(0, policy.padding.max)
            if pad_len:
                seg += b"A" * pad_len  # padding bytes are arbitrary, HTTP ignores them
        segments.append(seg)
        pos += seg_len

    return segments


def _send_segments(
    sock: socket.socket,
    segments: List[bytes],
    policy: C3Policy,
    rng: random.Random,
) -> None:
    """
    Send all segments with random jitter between sends based on policy.
    """
    max_delay_s = policy.timing.max_delay_ms / 1000.0
    for idx, seg in enumerate(segments, start=1):
        before = time.time()
        sent = sock.send(seg)
        after = time.time()
        if sent != len(seg):
            LOGGER.warning(
                "Partial send: expected %d bytes, sent %d bytes (segment %d)",
                len(seg),
                sent,
                idx,
            )
        LOGGER.debug(
            "Segment %d: size=%d bytes, send_time=%.6f s",
            idx,
            sent,
            after - before,
        )
        if max_delay_s > 0 and idx < len(segments):
            delay = rng.random() * max_delay_s
            LOGGER.debug("Sleeping for %.6f s before next segment", delay)
            time.sleep(delay)


def _drain_response(sock: socket.socket) -> None:
    """
    Read and discard the response from the remote server.
    """
    while True:
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            LOGGER.warning("Socket timeout while reading response")
            break
        if not chunk:
            break


def _configure_logging(verbose: bool) -> None:
    """
    Configure root logging handler and level.
    """
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)


def parse_args(argv: Optional[list]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="C3 Core Obfuscation Client (production-grade HTTP over TCP sender)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Target host to connect to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9001,
        help="Target TCP port to connect to (default: 9001)",
    )
    parser.add_argument(
        "--path",
        default="/",
        help="HTTP path to request (default: /)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of requests to send (default: 1)",
    )
    parser.add_argument(
        "--mode",
        choices=("baseline", "obfuscate"),
        default="baseline",
        help="Traffic mode: baseline or obfuscate (default: baseline)",
    )
    parser.add_argument(
        "--policy",
        default=None,
        help="Path to C3 policy JSON file (used in obfuscate mode)",
    )
    parser.add_argument(
        "--rng-seed",
        type=int,
        default=None,
        help="Optional RNG seed for reproducible segmentation",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list]] = None) -> int:
    args = parse_args(argv)
    _configure_logging(args.verbose)

    LOGGER.info("C3 Core client starting (mode=%s)", args.mode)
    try:
        if args.mode == "baseline":
            send_baseline(args.host, args.port, path=args.path, count=args.count)
        else:
            policy = load_policy(args.policy)
            send_obfuscated(
                args.host,
                args.port,
                policy=policy,
                path=args.path,
                count=args.count,
                rng_seed=args.rng_seed,
            )
    except Exception as exc:
        LOGGER.error("Fatal error: %s", exc, exc_info=args.verbose)
        return 1

    LOGGER.info("C3 Core client finished successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
