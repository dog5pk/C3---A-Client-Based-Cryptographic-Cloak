#!/usr/bin/env python3
import argparse
import time
import os
import json
import traceback
from datetime import datetime
from analyzer import analyze_run
from policy import AdaptivePolicy

DEVICE_ID = os.getenv("C3_DEVICE_ID", "device-1")
HOOK_SCRIPT = "./run_real_obfuscation.sh"
HOOK_TIMEOUT = int(os.getenv("C3_HOOK_TIMEOUT", "20"))

def run_simulated_cycle(params):
    import random
    now = time.time()
    packets = []
    total_pkts = random.randint(20, 80)
    ts = now
    for _ in range(total_pkts):
        size = random.randint(params['min_seg'], params['max_seg'])
        if random.random() < 0.3:
            size += random.randint(0, params.get('max_pad', 0))
        jitter = random.uniform(0, params.get('delay_ms', 0) / 1000.0)
        ts += jitter + random.expovariate(1 / 0.01)
        packets.append({"ts": ts, "size": size})
    return packets

def run_hook_cycle(params):
    import subprocess
    if not (os.path.exists(HOOK_SCRIPT) and os.access(HOOK_SCRIPT, os.X_OK)):
        return None
    env = os.environ.copy()
    env.update({f"C3_PARAM_{k.upper()}": str(v) for k, v in params.items()})
    try:
        proc = subprocess.run([HOOK_SCRIPT], capture_output=True, text=True, env=env, timeout=HOOK_TIMEOUT)
        out = proc.stdout.strip()
        if not out:
            cand = proc.stderr.strip()
            if cand and os.path.exists(cand):
                with open(cand, "r") as f:
                    data = json.load(f)
                    return data
            return None
        try:
            data = json.loads(out)
            if isinstance(data, list):
                return data
        except Exception:
            if os.path.exists(out):
                with open(out, "r") as f:
                    data = json.load(f)
                    return data
        return None
    except Exception:
        return None

def run_obfuscation_cycle(params):
    hook_result = run_hook_cycle(params)
    if hook_result:
        return hook_result
    return run_simulated_cycle(params)

def ascii_confidence_curve(history):
    cols = 50
    s = ""
    for v in history[-24:]:
        filled = int(v * cols)
        s += "[" + "#" * filled + "-" * (cols - filled) + f"] {v:.2f}\n"
    return s

def adaptive_loop(duration_seconds: int, device_id: str, debug: bool = False):
    # construct policy (policy.AdaptivePolicy accepts device_id)
    policy = AdaptivePolicy(device_id=device_id)
    start = time.time()
    end = start + duration_seconds
    confidence_history = []
    params = policy.params
    cycle = 0

    print(f"Starting adaptive mode for {duration_seconds}s (device {device_id})")
    print("Initial params:", params)

    try:
        while time.time() < end:
            cycle += 1
            packets = run_obfuscation_cycle(params)
            metrics = analyze_run(packets, save_json=True)
            # use the new policy.update(...) API
            result = policy.update(metrics)
            params = result.get('params', params)
            stealth_pred = result.get('stealth_pred', 0.5)
            entropy = metrics.get('entropy_size', 0.0)
            privacy_conf = (stealth_pred * 0.6) + (min(entropy / 8.0, 1.0) * 0.4)
            privacy_conf = max(0.0, min(1.0, privacy_conf))
            confidence_history.append(privacy_conf)
            # record run in profile
            try:
                policy.record_run(params, metrics, stealth_score=privacy_conf)
            except Exception:
                # best-effort; don't crash if profile write fails
                pass

            # print short status
            print(f"\n[cycle {cycle}] {datetime.utcnow().isoformat()} metrics:")
            print(f" avg_gap={metrics.get('avg_gap',0):.4f}s std_gap={metrics.get('std_gap',0):.4f} entropy={metrics.get('entropy_size',0):.2f}")
            print(f" burst_var={metrics.get('burst_variance',0):.2f} gap_ac={metrics.get('gap_autocorr',0):.3f}")
            print(f" stealth_pred={stealth_pred:.3f} privacy_conf={privacy_conf:.3f}")
            print(" new params:", params)
            print(ascii_confidence_curve(confidence_history))
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Adaptive run interrupted by user.")
    except Exception:
        tb = traceback.format_exc()
        if debug:
            with open("last_run.log", "w") as f:
                f.write(tb)
            print("Unhandled error during adaptive loop. Trace written to last_run.log")
        else:
            print("Unhandled error during adaptive loop. Rerun with --debug to capture traceback.")
        raise

    summary = {
        "device_id": device_id,
        "cycles": cycle,
        "final_params": params,
        "privacy_confidence_history": confidence_history,
        "end_time": time.time()
    }
    outp = os.path.join(os.getcwd(), f"adaptive_summary_{device_id}_{int(time.time())}.json")
    with open(outp, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nAdaptive run complete. Summary written to {outp}")

def main():
    parser = argparse.ArgumentParser(description="C3 obfuscator client")
    parser.add_argument("--mode", choices=["normal", "adaptive"], default="normal")
    parser.add_argument("--duration", type=int, default=300)
    parser.add_argument("--debug", action="store_true", help="write traceback to last_run.log on error")
    args = parser.parse_args()
    if args.mode == "adaptive":
        adaptive_loop(args.duration, DEVICE_ID, debug=args.debug)
    else:
        print("Normal mode. Use --mode adaptive for self-tuning loop.")

if __name__ == "__main__":
    main()
