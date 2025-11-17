#!/usr/bin/env python3
"""
export_policy_from_trend.py

Freeze the current best parameters from the adaptive engine into a
C3 policy file (c3_policy.json) suitable for use by the C3 Core client.

Expected input:
  - adaptive_trend_summary.json in the current directory.
    This file should contain either:
      - a "final_params" object with tuned values, or
      - top-level parameter keys.

The script does NOT modify your adaptive loop. It just reads the latest
trend summary and emits a policy snapshot.

This is designed to be production-grade:
  - explicit validation
  - clear logging
  - safe fallbacks if keys are missing
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

DEFAULT_MIN_SEG = 16
DEFAULT_MAX_SEG = 64
DEFAULT_MAX_PAD = 16
DEFAULT_MAX_DELAY_MS = 5.0

TREND_FILE = Path("adaptive_trend_summary.json")
POLICY_FILE = Path("c3_policy.json")

LOGGER = logging.getLogger("export_policy")


def _configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)


def load_trend() -> Dict[str, Any]:
    if not TREND_FILE.is_file():
        raise FileNotFoundError(f"Trend summary not found: {TREND_FILE}")
    LOGGER.info("Loading trend summary from %s", TREND_FILE)
    with TREND_FILE.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse {TREND_FILE}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"Expected object at top-level of {TREND_FILE}, got {type(data)}")
    return data


def extract_params(trend: Dict[str, Any]) -> Dict[str, float]:
    """
    Try to extract tuned parameters from the trend summary.

    We first look for trend["final_params"], and fall back to top-level keys
    if not present. Missing parameters are filled with defaults.
    """
    params = trend.get("final_params")
    if params is None or not isinstance(params, dict):
        LOGGER.warning("No 'final_params' object found; falling back to top-level keys")
        params = trend

    def get_num(key: str, default: float) -> float:
        value = params.get(key)
        if value is None:
            LOGGER.warning("Parameter '%s' missing; using default=%s", key, default)
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            LOGGER.warning("Parameter '%s' invalid (%r); using default=%s", key, value, default)
            return default

    # Try to map likely key names; if they don't exist, defaults are used.
    min_seg = get_num("min_seg_bytes", DEFAULT_MIN_SEG)
    max_seg = get_num("max_seg_bytes", DEFAULT_MAX_SEG)
    max_pad = get_num("max_pad_bytes", DEFAULT_MAX_PAD)

    # Some engines might store delay as ms or seconds; check both sanely.
    delay_ms = None
    raw_ms = params.get("max_delay_ms")
    raw_s = params.get("max_delay_s")

    if raw_ms is not None:
        try:
            delay_ms = float(raw_ms)
        except (TypeError, ValueError):
            LOGGER.warning("Parameter 'max_delay_ms' invalid (%r); ignoring", raw_ms)
            delay_ms = None

    if delay_ms is None and raw_s is not None:
        try:
            delay_s = float(raw_s)
            delay_ms = delay_s * 1000.0
        except (TypeError, ValueError):
            LOGGER.warning("Parameter 'max_delay_s' invalid (%r); ignoring", raw_s)
            delay_ms = None

    if delay_ms is None:
        LOGGER.warning("No valid delay parameter found; using default=%s ms", DEFAULT_MAX_DELAY_MS)
        delay_ms = DEFAULT_MAX_DELAY_MS

    # Basic sanity: ensure min_seg <= max_seg
    if min_seg <= 0:
        LOGGER.warning("min_seg_bytes <= 0 (%s); clamping to 1", min_seg)
        min_seg = 1
    if max_seg < min_seg:
        LOGGER.warning(
            "max_seg_bytes < min_seg_bytes (%s < %s); setting max_seg_bytes = min_seg_bytes",
            max_seg,
            min_seg,
        )
        max_seg = min_seg

    if max_pad < 0:
        LOGGER.warning("max_pad_bytes < 0 (%s); clamping to 0", max_pad)
        max_pad = 0.0

    return {
        "min_seg_bytes": float(min_seg),
        "max_seg_bytes": float(max_seg),
        "max_pad_bytes": float(max_pad),
        "max_delay_ms": float(delay_ms),
    }


def build_policy(params: Dict[str, float], trend: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a C3 policy document from parameters and trend metadata.
    """
    profile_name = trend.get("profile_name") or trend.get("best_profile") or "adaptive-snapshot"
    stealth_conf = trend.get("mean_confidence") or trend.get("stealth_confidence") or 0.0
    last_updated = trend.get("last_updated") or trend.get("timestamp") or "unknown"

    policy = {
        "version": "c3-policy-v1",
        "profile_name": str(profile_name),
        "segment": {
            "min": int(params["min_seg_bytes"]),
            "max": int(params["max_seg_bytes"]),
        },
        "padding": {
            "max": int(params["max_pad_bytes"]),
        },
        "timing": {
            "max_delay_ms": float(params["max_delay_ms"]),
        },
        "meta": {
            "source": "adaptive_trend_summary",
            "stealth_confidence": float(stealth_conf),
            "last_updated": str(last_updated),
        },
    }
    return policy


def write_policy(policy: Dict[str, Any]) -> None:
    LOGGER.info("Writing C3 policy to %s", POLICY_FILE)
    with POLICY_FILE.open("w", encoding="utf-8") as f:
        json.dump(policy, f, indent=2, sort_keys=True)
    LOGGER.info("Policy snapshot written successfully")


def main() -> int:
    _configure_logging()
    LOGGER.info("Exporting C3 policy from adaptive trend summary")
    try:
        trend = load_trend()
        params = extract_params(trend)
        policy = build_policy(params, trend)
        write_policy(policy)
    except Exception as exc:
        LOGGER.error("Fatal error: %s", exc)
        return 1
    LOGGER.info("Export complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
