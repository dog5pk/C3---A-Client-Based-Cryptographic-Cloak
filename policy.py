#!/usr/bin/env python3
"""
policy.py — Adaptive policy engine (entropy-weighted)
Compatible with obfuscator_client.py which constructs AdaptivePolicy(device_id=...)
"""

import json, os, statistics, math, time
from typing import Dict, Any, List

# Default safe parameter bounds
DEFAULTS = {
    "min_seg": 64,
    "max_seg": 2048,
    "max_pad": 1000,
    "delay_ms": 20,
}

BOUNDS = {
    "min_seg": (16, 512),
    "max_seg": (512, 4096),
    "max_pad": (0, 3000),
    "delay_ms": (1, 250),
}

WINDOW_SIZE = 5  # recent runs to smooth adjustments


def clamp(v, low, high):
    return max(low, min(high, v))


def moving_avg(seq: List[float]) -> float:
    seq = [x for x in seq if isinstance(x, (int, float))]
    if not seq:
        return 0.0
    return sum(seq) / len(seq)


class AdaptivePolicy:
    """
    AdaptivePolicy can be constructed either as:
       AdaptivePolicy(device_id="my-device")
    or
       AdaptivePolicy(profile_path="~/.c3_profiles/my-device.json")
    It stores profile at ~/.c3_profiles/<device_id>.json by default.
    """
    def __init__(self, device_id: str = None, profile_path: str = None, window_size: int = WINDOW_SIZE):
        self.window_size = window_size
        # decide profile path
        if profile_path:
            self.profile_path = os.path.expanduser(profile_path)
        else:
            if not device_id:
                device_id = "device-1"
            prof_dir = os.path.expanduser(os.getenv("C3_PROFILE_DIR", "~/.c3_profiles"))
            os.makedirs(prof_dir, exist_ok=True)
            self.profile_path = os.path.join(prof_dir, f"{device_id}.json")
        self.recent_metrics: List[Dict[str, Any]] = []
        self.params = DEFAULTS.copy()
        self._load_profile()

    def _load_profile(self):
        if not os.path.exists(self.profile_path):
            return
        try:
            with open(self.profile_path, "r") as f:
                prof = json.load(f)
            runs = prof.get("runs", [])
            if runs:
                last = runs[-1]
                # only update known params
                for k in ("min_seg","max_seg","max_pad","delay_ms"):
                    if k in last.get("params", {}):
                        self.params[k] = last["params"][k]
        except Exception:
            pass

    def _save_profile(self):
        # noop here; profile written elsewhere by policy.record_run in client
        try:
            if not os.path.exists(os.path.dirname(self.profile_path)):
                os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
        except Exception:
            pass

    def record_run(self, params: Dict, metrics: Dict, stealth_score: float = None):
        # minimal append to profile file (best-effort)
        try:
            rec = {"params": params, "metrics": metrics, "timestamp": time.time()}
            if stealth_score is not None:
                rec["stealth_score"] = stealth_score
            if os.path.exists(self.profile_path):
                with open(self.profile_path, "r") as f:
                    prof = json.load(f)
            else:
                prof = {"runs": []}
            prof.setdefault("runs", []).append(rec)
            # keep bounded
            if len(prof["runs"]) > 2000:
                prof["runs"] = prof["runs"][-2000:]
            with open(self.profile_path, "w") as f:
                json.dump(prof, f, indent=2)
        except Exception:
            pass

    def update(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Use latest analyzer metrics to adjust parameters."""
        # guard: normalize numeric fields
        safe_metrics = {}
        for k,v in (metrics or {}).items():
            safe_metrics[k] = v if isinstance(v, (int,float)) else 0.0
        metrics = safe_metrics

        self.recent_metrics.append(metrics)
        if len(self.recent_metrics) > self.window_size:
            self.recent_metrics.pop(0)

        avg_entropy = moving_avg([m.get("entropy_size", 0) for m in self.recent_metrics])
        avg_burst = moving_avg([m.get("burst_variance", 0) for m in self.recent_metrics])
        avg_gap = moving_avg([m.get("avg_gap", 0) for m in self.recent_metrics])
        avg_stdgap = moving_avg([m.get("std_gap", 0) for m in self.recent_metrics])

        new_params = dict(self.params)

        # Entropy drive — push toward higher variability
        if avg_entropy < 5.0:
            factor = (5.0 - avg_entropy) / 5.0
            new_params["min_seg"] = int(clamp(new_params["min_seg"] * (1 - 0.3 * factor), *BOUNDS["min_seg"]))
            new_params["max_seg"] = int(clamp(new_params["max_seg"] * (1 + 0.5 * factor), *BOUNDS["max_seg"]))
        else:
            # entropy already high — mild convergence
            new_params["min_seg"] = int(clamp(new_params["min_seg"] * 1.05, *BOUNDS["min_seg"]))
            new_params["max_seg"] = int(clamp(new_params["max_seg"] * 0.98, *BOUNDS["max_seg"]))

        # Padding and delay control — reduce if latency spikes
        if avg_gap > 0.02 or avg_stdgap > 0.02:
            new_params["max_pad"] = int(clamp(new_params["max_pad"] * 0.85, *BOUNDS["max_pad"]))
            new_params["delay_ms"] = int(clamp(new_params["delay_ms"] * 0.9, *BOUNDS["delay_ms"]))
        else:
            new_params["max_pad"] = int(clamp(new_params["max_pad"] * 1.1, *BOUNDS["max_pad"]))
            new_params["delay_ms"] = int(clamp(new_params["delay_ms"] * 1.05, *BOUNDS["delay_ms"]))

        # burst variance control — large variance → tighten segmentation
        if avg_burst > 50:
            new_params["max_seg"] = int(clamp(new_params["max_seg"] * 0.95, *BOUNDS["max_seg"]))
            new_params["min_seg"] = int(clamp(new_params["min_seg"] * 1.05, *BOUNDS["min_seg"]))

        self.params = new_params
        # stealth_pred placeholder (no regressor here)
        stealth_pred = 0.5
        return {"params": new_params, "stealth_pred": stealth_pred, "aggregates": {
            "avg_entropy": avg_entropy, "avg_burst": avg_burst, "avg_gap": avg_gap, "avg_stdgap": avg_stdgap
        }}


def get_policy(device_id: str = "my-device", profile_dir: str = None) -> AdaptivePolicy:
    if profile_dir:
        profile_path = os.path.join(os.path.expanduser(profile_dir), f"{device_id}.json")
    else:
        profile_path = None
    return AdaptivePolicy(device_id=device_id, profile_path=profile_path)
