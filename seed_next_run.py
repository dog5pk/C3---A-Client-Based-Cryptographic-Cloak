import json, subprocess

trend = "adaptive_trend_summary.json"
summary_out = "adaptive_summary_my-device_next.json"

with open(trend) as f:
    data = json.load(f)

params = data.get("last_params", {})
if not params:
    raise RuntimeError("No parameters found in trend summary.")

print(f"Seeding next adaptive cycle with: {params}")

cmd = [
    "python3", "adaptive_main.py",
    "--min-seg", str(params["min_seg"]),
    "--max-seg", str(params["max_seg"]),
    "--max-pad", str(params["max_pad"]),
    "--delay-ms", str(params["delay_ms"]),
    "--save-summary", summary_out
]

print("Running adaptive main with tuned parameters...")
subprocess.run(cmd, check=True)
print(f"\nNext summary stored at: {summary_out}")
