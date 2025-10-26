#!/usr/bin/env python3
"""
feature_extractor.py

Feature extraction for website-fingerprinting experiments.

This script walks through a directory of packet capture (PCAP) files,
computes a set of simple aggregate features from each capture, and
writes the results to a CSV file. The extracted features include
packet size statistics and inter-arrival time statistics for each
capture, as commonly used in website-fingerprinting research.

Directory layout expected:
dataset_dir/
  label_a/
    sample1.pcap
    sample2.pcap
  label_b/
    sample3.pcap

Output CSV columns:
label,num_packets,total_bytes,mean_size,median_size,std_size,
num_outgoing,num_incoming,mean_inter_arrival,median_inter_arrival,std_inter_arrival

Requires: scapy, numpy, pandas
Install: pip install scapy numpy pandas
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Dict, List, Tuple, Optional

try:
    from scapy.all import rdpcap, IP
except Exception:
    print("scapy is required. Install with: pip install scapy", file=sys.stderr)
    sys.exit(1)

try:
    import numpy as np
except Exception:
    print("numpy is required. Install with: pip install numpy", file=sys.stderr)
    sys.exit(1)


def extract_features_from_pcap(pcap_path: str) -> Optional[Dict[str, float]]:
    """
    Extract aggregate features from a single PCAP file.
    Returns a dict of features or None if no IP packets found / read failed.
    """
    try:
        packets = rdpcap(pcap_path)
    except Exception as e:
        print(f"[warn] failed to read {pcap_path}: {e}", file=sys.stderr)
        return None

    pkt_times: List[float] = []
    pkt_sizes: List[int] = []
    client_ip: Optional[str] = None

    for pkt in packets:
        if not pkt.haslayer(IP):
            continue
        ip_layer = pkt[IP]
        size = len(pkt)
        if client_ip is None:
            client_ip = ip_layer.src
        direction = 1 if ip_layer.src == client_ip else -1
        pkt_times.append(float(pkt.time))
        pkt_sizes.append(int(size) * direction)

    if not pkt_sizes:
        return None

    # inter-arrival times in seconds
    inter_arrivals = [pkt_times[i] - pkt_times[i - 1] for i in range(1, len(pkt_times))]

    arr_sizes = np.array(pkt_sizes, dtype=float)
    arr_inter = np.array(inter_arrivals, dtype=float) if inter_arrivals else np.array([])

    feats: Dict[str, float] = {
        "num_packets": float(len(arr_sizes)),
        "total_bytes": float(arr_sizes.sum()),
        "mean_size": float(arr_sizes.mean()),
        "median_size": float(np.median(arr_sizes)),
        "std_size": float(arr_sizes.std(ddof=0)),
        "num_outgoing": float(np.sum(arr_sizes > 0)),
        "num_incoming": float(np.sum(arr_sizes < 0)),
    }

    if arr_inter.size > 0:
        feats.update({
            "mean_inter_arrival": float(arr_inter.mean()),
            "median_inter_arrival": float(np.median(arr_inter)),
            "std_inter_arrival": float(arr_inter.std(ddof=0)),
        })
    else:
        feats.update({
            "mean_inter_arrival": 0.0,
            "median_inter_arrival": 0.0,
            "std_inter_arrival": 0.0,
        })

    return feats


def process_dataset(dataset_dir: str) -> Tuple[List[str], List[Dict[str, float]]]:
    """
    Walk dataset_dir and extract features for each pcap under each label directory.
    Returns (labels, feature_dicts).
    """
    labels: List[str] = []
    feature_dicts: List[Dict[str, float]] = []

    for root, dirs, files in os.walk(dataset_dir):
        rel = os.path.relpath(root, dataset_dir)
        if rel == ".":
            continue
        label = os.path.basename(root)
        for fname in sorted(files):
            if not (fname.lower().endswith(".pcap") or fname.lower().endswith(".pcapng")):
                continue
            pcap_path = os.path.join(root, fname)
            feats = extract_features_from_pcap(pcap_path)
            if feats is None:
                continue
            labels.append(label)
            feature_dicts.append(feats)

    return labels, feature_dicts


def write_csv(labels: List[str], feats: List[Dict[str, float]], out_csv: str) -> None:
    """Write features and labels to CSV (header: label + sorted feature names)."""
    if not feats:
        print("[error] no features extracted", file=sys.stderr)
        return
    fieldnames = list(sorted(feats[0].keys()))
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["label"] + fieldnames)
        for label, feat in zip(labels, feats):
            row = [label] + [feat.get(name, 0.0) for name in fieldnames]
            writer.writerow(row)
    print(f"[info] wrote {len(labels)} samples to {out_csv}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract features from PCAP dataset for website fingerprinting")
    parser.add_argument("dataset_dir", help="Path to dataset directory with subdirectories per class")
    parser.add_argument("output_csv", help="Path to output CSV file")
    args = parser.parse_args()

    labels, feats = process_dataset(args.dataset_dir)
    if not labels:
        print("[error] no PCAP files processed", file=sys.stderr)
        sys.exit(1)
    write_csv(labels, feats, args.output_csv)


if __name__ == "__main__":
    main()
