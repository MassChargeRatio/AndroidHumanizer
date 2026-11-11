# -*- coding: utf-8 -*-
"""Default configuration and dict merge. No YAML dependency.

默认配置与字典合并。不引入 YAML 依赖。
"""
from __future__ import annotations

import copy
from typing import Any


# Default values for the three sub-modules.
# 三个子模块的默认值。
DEFAULTS: dict[str, Any] = {
    "kinematics": {
        "enabled": True,
        "steps_min": 20,
        "steps_max": 60,
        "px_per_step": 15.0,
        "duration_per_px": 0.0007,
        "duration_min": 0.3,
        "duration_max": 1.5,
        "perpendicular_ratio": 0.12,
        "use_ease_in_out": True,
        "jitter_sigma": 1.2,
        "jitter_tail_fraction": 0.25,
        "overshoot_prob": 0.25,
        "overshoot_ratio": 0.06,
    },
    "timing": {
        "mu_ratio": 0.18,
        "sigma_range": (0.45, 0.75),
        "delay_between_actions": (0.6, 2.2),
        "delay_after_open": (3.0, 6.0),
        "think_delay": (1.5, 4.0),
        "start_jitter": (0, 600),
        "wake_window": {"start": "07:30", "end": "23:00"},
        "cooldown_every": 12,
        "cooldown_seconds": 20.0,
        "cooldown_on_captcha": 300.0,
    },
    "sensors": {
        "fs": 100.0,
        "duration": 5.0,
        "mode": "resting",
        "dead_std_threshold": 0.02,
        "gyro_dead_std": 0.001,
        "dead_zero_ratio_max": 0.9,
    },
}


def _merge(base: dict, override: dict) -> dict:
    # Deep-merge; nested dicts are merged recursively, others replaced.
    # 深合并：嵌套 dict 递归合并，其余直接替换。
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def merge_config(config: dict | None = None) -> dict:
    """User config overrides defaults (deep merge, returns a new dict).

    用户配置覆盖默认值（深合并，返回新 dict）。
    """
    return _merge(DEFAULTS, config or {})
