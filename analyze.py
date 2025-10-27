#!/usr/bin/env python3
# Minimal analyzer to regenerate plots/summary from logs
import json, argparse
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt

def ecdf(data):
    x = np.sort(data); y = np.arange(1, len(x)+1) / len(x); return x, y
def save_hist_ecdf(series, label, xlabel, out_png, bins=50, logx=False):
    import numpy as np, matplotlib.pyplot as plt
    data = np.asarray(series); data = data[np.isfinite(data)]
    if logx: data = data[data>0]
    plt.figure(figsize=(7,5)); plt.hist(data, bins=bins, alpha=0.6, edgecolor='black')
    if logx: plt.xscale('log')
    plt.xlabel(xlabel); plt.ylabel('Count'); plt.title(f'{label} — Histogram')
    plt.tight_layout(); plt.savefig(out_png, dpi=140); plt.close()
    x,y = ecdf(data); plt.figure(figsize=(7,5)); plt.plot(x,y,linewidth=2)
    if logx: plt.xscale('log')
    plt.xlabel(xlabel); plt.ylabel('ECDF'); plt.title(f'{label} — ECDF')
    plt.tight_layout(); plt.savefig(str(out_png).replace('.png','_ecdf.png'), dpi=140); plt.close()
def save_box(series, label, xlabel, out_png, logy=False):
    import numpy as np, matplotlib.pyplot as plt
    data = np.asarray(series); data = data[np.isfinite(data)]
    if logy: data = data[data>0]
    plt.figure(figsize=(7,5)); plt.boxplot(data, vert=True, showfliers=False)
    plt.xticks([1],[xlabel]); 
    if logy: plt.yscale('log'); plt.ylabel('Log scale')
    else: plt.ylabel('Value')
    plt.title(f'{label} — Boxplot'); plt.tight_layout(); plt.savefig(out_png, dpi=140); plt.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', required=True)
    ap.add_argument('--obfuscate', required=True)
    ap.add_argument('--outdir', default='plots')
    ap.add_argument('--summary', default='summary.json')
    a = ap.parse_args()
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    dfb = pd.read_csv(a.baseline); dfo = pd.read_csv(a.obfuscate)
    save_hist_ecdf(dfb['size_bytes'], 'Baseline Sizes','Packet size (bytes)', out / 'baseline_sizes_hist.png', logx=False)
    save_hist_ecdf(dfb['gap_ms'], 'Baseline Gaps','Inter-packet gap (ms)', out / 'baseline_gaps_hist.png', logx=True)
    save_box(dfb['size_bytes'], 'Baseline Sizes','Packet size (bytes)', out / 'baseline_sizes_box.png', logy=False)
    save_box(dfb['gap_ms'], 'Baseline Gaps','Inter-packet gap (ms)', out / 'baseline_gaps_box.png', logy=True)
    save_hist_ecdf(dfo['size_bytes'], 'C3 Obfuscate Sizes','Packet size (bytes)', out / 'obfuscate_sizes_hist.png', logx=False)
    save_hist_ecdf(dfo['gap_ms'], 'C3 Obfuscate Gaps','Inter-packet gap (ms)', out / 'obfuscate_gaps_hist.png', logx=True)
    save_box(dfo['size_bytes'], 'C3 Obfuscate Sizes','Packet size (bytes)', out / 'obfuscate_sizes_box.png', logy=False)
    save_box(dfo['gap_ms'], 'C3 Obfuscate Gaps','Inter-packet gap (ms)', out / 'obfuscate_gaps_box.png', logy=True)
    # simple metrics
    def hist_prob(data, bins):
        hist, edges = np.histogram(data, bins=bins, density=True)
        widths = np.diff(edges); p = hist * widths; p = p / p.sum(); return p
    def kl_div(p, q, eps=1e-12):
        p = np.clip(p, eps, 1.0); q = np.clip(q, eps, 1.0)
        return float(np.sum(p * np.log(p / q)))
    def js_div(p, q):
        m = 0.5*(p+q); return 0.5*kl_div(p,m) + 0.5*kl_div(q,m)
    bins_sizes = np.linspace(0, 1600, 80); bins_gaps = np.geomspace(1, 5000, 60)
    metrics = {
        'baseline': {'size_bytes_mean': float(dfb['size_bytes'].mean()),
                     'size_bytes_std': float(dfb['size_bytes'].std()),
                     'gap_ms_median': float(np.median(dfb['gap_ms'])),
                     'gap_ms_p95': float(np.percentile(dfb['gap_ms'],95))},
        'obfuscate': {'size_bytes_mean': float(dfo['size_bytes'].mean()),
                      'size_bytes_std': float(dfo['size_bytes'].std()),
                      'gap_ms_median': float(np.median(dfo['gap_ms'])),
                      'gap_ms_p95': float(np.percentile(dfo['gap_ms'],95))},
        'divergence': {'size_bytes_js_divergence': float(js_div(hist_prob(dfb['size_bytes'], bins_sizes),
                                                                hist_prob(dfo['size_bytes'], bins_sizes))),
                       'gap_ms_js_divergence': float(js_div(hist_prob(dfb['gap_ms'], bins_gaps),
                                                            hist_prob(dfo['gap_ms'], bins_gaps)))}}
    Path(a.summary).write_text(json.dumps(metrics, indent=2))
if __name__ == '__main__':
    main()
