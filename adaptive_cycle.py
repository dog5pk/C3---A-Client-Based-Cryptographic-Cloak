import subprocess, time, os, json, traceback, zipfile
from datetime import datetime

def run(cmd):
    try:
        print(f"\n[RUN] {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {' '.join(cmd)}")
        print(e)
        time.sleep(60)

def make_backup():
    os.makedirs("backups", exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    archive = os.path.join("backups", f"c3_state_{stamp}.zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in os.listdir("."):
            if fn.endswith(".json") or fn.endswith(".py") or fn.endswith(".log"):
                z.write(fn)
    print(f"[BACKUP] Created {archive}")

cycle_count = 0
backup_interval = 5  # create a backup every 5 cycles

while True:
    try:
        cycle_count += 1
        print(f"\n=== Starting Adaptive Cycle {cycle_count} ===")

        # Step 1: adaptive run
        run(["python3", "adaptive_main.py"])

        # Step 2: merge summaries
        run(["python3", "merge_summaries.py"])

        # Step 3: reseed
        if os.path.exists("adaptive_trend_summary.json"):
            with open("adaptive_trend_summary.json") as f:
                data = json.load(f)
            params = data.get("last_params", {})
            if params:
                cmd = [
                    "python3", "adaptive_main.py",
                    "--min-seg", str(params["min_seg"]),
                    "--max-seg", str(params["max_seg"]),
                    "--max-pad", str(params["max_pad"]),
                    "--delay-ms", str(params["delay_ms"]),
                    "--save-summary", "adaptive_summary_my-device_next.json"
                ]
                run(cmd)
            else:
                print("[WARN] No valid parameters found in trend summary.")
        else:
            print("[WARN] Trend summary not found; skipping reseed.")

        # Step 4: backup every N cycles
        if cycle_count % backup_interval == 0:
            make_backup()

    except Exception:
        print("\n[UNHANDLED ERROR]")
        traceback.print_exc()
        print("Sleeping 120s before retry...")
        time.sleep(120)

    print("\nCycle complete. Sleeping 60s before next run...")
    time.sleep(60)
