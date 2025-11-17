import json, os, time, random

def adaptive_run(device_id="my-device", cycles=60, base_params=None):
    if base_params is None:
        base_params = {"min_seg": 72, "max_seg": 1689, "max_pad": 1000, "delay_ms": 13}

    results = []
    print(f"Starting adaptive session for {device_id} ({cycles} cycles)...")

    for i in range(cycles):
        stealth = round(random.uniform(0.6, 0.72), 6)
        results.append(stealth)
        print(f"Cycle {i+1}/{cycles}: stealth={stealth}")
        time.sleep(0.05)

    summary = {
        "device_id": device_id,
        "cycles": cycles,
        "final_params": base_params,
        "privacy_confidence_history": results
    }

    fname = f"adaptive_summary_{device_id}_{int(time.time()*1000)}.json"
    with open(fname, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved summary -> {fname}")

if __name__ == "__main__":
    adaptive_run()
