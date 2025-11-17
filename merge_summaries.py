import json, glob, statistics, os

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Skipping {path}: {e}")
        return None

def summarize():
    files = sorted(glob.glob("adaptive_summary_my-device_*.json"))
    if not files:
        print("No adaptive summary files found.")
        return

    print(f"Found {len(files)} adaptive summaries.")
    data = [load_json(f) for f in files]
    data = [d for d in data if d]

    all_scores = []
    all_privacy = []
    all_params = []

    for d in data:
        scores = d.get("privacy_confidence_history", [])
        if scores:
            all_scores.append(statistics.mean(scores))
        if "final_params" in d:
            all_params.append(d["final_params"])

    # Aggregate summary
    result = {
        "file_count": len(data),
        "avg_confidence_overall": round(statistics.mean(all_scores), 6) if all_scores else None,
        "max_confidence": round(max(all_scores), 6) if all_scores else None,
        "min_confidence": round(min(all_scores), 6) if all_scores else None,
        "last_params": all_params[-1] if all_params else {},
    }

    out_path = "adaptive_trend_summary.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nMerged summary saved to: {out_path}")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    summarize()
