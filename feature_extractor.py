#!/usr/bin/env python3
from typing import List, Dict
import math
import statistics
from collections import Counter

def entropy(values):
    if not values:
        return 0.0
    cnt = Counter(values)
    total = sum(cnt.values())
    ent = 0.0
    for c in cnt.values():
        p = c / total
        ent -= p * math.log2(p)
    return ent

def gap_series(packets: List[Dict]):
    if len(packets) < 2:
        return []
    packets_sorted = sorted(packets, key=lambda p: p['ts'])
    return [packets_sorted[i]['ts'] - packets_sorted[i-1]['ts'] for i in range(1, len(packets_sorted))]

def burst_lengths(packets: List[Dict]):
    if len(packets) < 1:
        return []
    gaps = gap_series(packets)
    if not gaps:
        return [len(packets)]
    median_gap = statistics.median(gaps)
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

def autocorr(series, lag=1):
    if not series or len(series) <= lag:
        return 0.0
    n = len(series)
    mean = sum(series) / n
    num = sum((series[i] - mean) * (series[i - lag] -*
cat > feature_extractor.py <<'PY'
#!/usr/bin/env python3
from typing import List, Dict
import math
import statistics
from collections import Counter

def entropy(values):
    if not values:
        return 0.0
    cnt = Counter(values)
    total = sum(cnt.values())
    ent = 0.0
    for c in cnt.values():
        p = c / total
        ent -= p * math.log2(p)
    return ent

def gap_series(packets: List[Dict]):
    if len(packets) < 2:
        return []
    packets_sorted = sorted(packets, key=lambda p: p['ts'])
    return [packets_sorted[i]['ts'] - packets_sorted[i-1]['ts'] for i in range(1, len(packets_sorted))]

def burst_lengths(packets: List[Dict]):
    if len(packets) < 1:
        return []
    gaps = gap_series(packets)
    if not gaps:
        return [len(packets)]
    median_gap = statistics.median(gaps)
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

def autocorr(series, lag=1):
    if not series or len(series) <= lag:
        return 0.0
    n = len(series)
    mean = sum(series) / n
    num = sum((series[i] - mean) * (series[i - lag] -*


