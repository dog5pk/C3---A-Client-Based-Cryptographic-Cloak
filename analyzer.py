#!/usr/bin/env python3
import json
import math
import os
import time
from typing import List, Dict
import statistics

OUTPUT_DIR = os.getenv("C3_ANALYZER_OUTPUT", "analyzer_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def _entropy_of_sizes(sizes: List[int]) -> float:
    if not sizes:
        return 0.0
    freq = {}
    for s in sizes:
        freq[s] = freq.get(s, 0) + 1
    total = len(sizes)
    ent = 0.0
    for count in freq.values():
        p = count / total
        ent -= p * math.log2(p)
    return ent

def _burst_lengths(packets: List[Dict]) -> List[int]:
    # define a burst boundary as a gap > median gap * 2 (heuristic)
    if len(packets) < 2:
        return [len(packets)]
    gaps = [packets[i]['ts'] - packets[i-1]['ts'] for i in range(1, len(packets))]
    median_gap = statistics.median(gaps) if gaps else 0.0
    bursts = []
    current = 1
    for g in gaps:
        if median_gap > 0 and g > median_gap * 2:
            bursts.append(current)
            current = 1
        else:
            current += 1
    bursts.append(current)
    return bursts

def _gap_autocorrelation(gaps: List[float], lag: int = 1) -> float:
    if len(gaps) <= lag:
        return 0.0
    n = len(gaps)
    mean = sum(gaps) / n
    num = sum((gaps[i] - mean) * (gaps[i - lag] - mean) for i in range(lag, n))
    den = sum((x - mean) ** 2 for x in gaps)
    return (num / den) if den != 0 else 0.0

def analyze_run(packets: List[Dict], save_json: bool = True) -> Dict:
    """
    packets: list of dicts with at least {'ts': float, 'size': int}
    returns: metrics dict
    """
    if not packets:
        metrics = {
            "avg_gap": 0.0,
            "std_gap": 0.0,
            "entropy_size": 0.0,
            "avg_pkt_size": 0.0,
            "total_pkts": 0,
            "burst_variance": 0.0,
            "gap_autocorr": 0.0,
            "timestamp": time.time()
        }
        if save_json:
            _write_metrics(metrics)
        return metrics

    packets_sorted = sorted(packets, key=lambda p: p['ts'])
    gaps = [packets_sorted[i]['ts'] - packets_sorted[i-1]['ts'] for i in range(1, len(packets_sorted))]
    sizes = [p['size'] for p in packets_sorted]

    avg_gap = statistics.mean(gaps) if gaps else 0.0
    std_gap = statistics.pstdev(gaps) if gaps else 0.0
    entropy_size = _entropy_of_sizes(sizes)
    avg_pkt_size = statistics.mean(sizes) if sizes else 0.0
    burst_lengths = _burst_lengths(packets_sorted)
    burst_variance = statistics.pvariance(burst_lengths) if len(burst_lengths) > 1 else 0.0
    gap_autocorr = _gap_autocorrelation(gaps, lag=1)

    metrics = {
        "avg_gap": avg_gap,
        "std_gap": std_gap,
        "entropy_size": entropy_size,
        "avg_pkt_size": avg_pkt_size,
        "total_pkts": len(packets_sorted),
        "burst_variance": burst_variance,
        "gap_autocorr": gap_autocorr,
        "timestamp": time.time()
    }
    if save_json:
        _write_metrics(metrics)
    return metrics

def _write_metrics(metrics: Dict):
    fname = os.path.join(OUTPUT_DIR, f"metrics_{int(metrics['timestamp'])}.json")
    try:
        with open(fname, "w") as f:
            json.dump(metrics, f, indent=2)
    except Exception:
        # best-effort: don't crash caller if write fails
        pass

if __name__ == "__main__":
    # quick smoke test when run directly
    sample = []
    now = time.time()
    for i in range(1, 11):
        sample.append({"ts": now + i * 0.01, "size": 100 + (i % 4) * 50})
    print(analyze_run(sample, save_json=False))
