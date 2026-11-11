# -*- coding: utf-8 -*-
"""Sensor sequence generation and "deadness" detection.

All randomness goes through the instance-level rng; global random.* is forbidden.

传感器序列生成与「死寂」检测。

所有随机消费走实例级 rng，禁止全局 random.*。
"""
from __future__ import annotations

import csv
import math
import random

__all__ = ["SensorProfile", "Sensors"]

# Supported motion modes.
# 支持的运动模式。
MODES = ("resting", "walking", "tapping", "scrolling")


def _smooth_pulse(t: float, center: float, width: float = 0.12) -> float:
    # Narrow pulse used to model taps / footfalls.
    # 用于模拟点按 / 步频冲击的窄脉冲。
    d = (t - center) / width
    if abs(d) > 1.0:
        return 0.0
    return math.cos(d * math.pi * 0.5) ** 2


def _axis_std(values) -> float:
    # Population standard deviation of a single axis.
    # 单轴总体标准差。
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / n)


def _zero_change_ratio(values) -> float:
    # Ratio of adjacent samples whose change is ~0 (a strong "dead" signal).
    # 相邻采样变化近似为 0 的比例（强「死寂」信号）。
    if len(values) < 2:
        return 1.0
    eps = 1e-9
    nz = 0
    for a, b in zip(values, values[1:]):
        if abs(b - a) <= eps:
            nz += 1
    return nz / (len(values) - 1)


class SensorProfile:
    """Generate a plausible sensor sequence (resting / walking / tapping / scrolling).

    生成一段拟真传感器序列（resting / walking / tapping / scrolling）。
    """

    def __init__(self, fs: float = 100.0, duration: float = 5.0,
                 mode: str = "resting", rng: random.Random | None = None):
        if mode not in MODES:
            raise ValueError(f"未知 mode={mode!r}，可选 {MODES}")
        # Instance-level rng; never touch global random.
        # 实例级 rng；不触碰全局 random。
        self.rng = rng or random.Random()
        self.fs = float(fs)
        self.duration = float(duration)
        self.mode = mode
        self.n = max(2, int(self.fs * self.duration))
        self._base = self._holding_orientation()
        self.rows = self._gen()

    def _holding_orientation(self):
        # Gravity vector in device coordinates with a small random tilt.
        # 设备坐标系下的重力分量，带少量随机倾斜。
        tilt = self.rng.gauss(0.0, 0.08)
        roll = self.rng.gauss(0.0, 0.05)
        g = 9.80665
        return (g * math.sin(tilt), g * math.sin(roll),
                g * math.cos(math.hypot(tilt, roll)))

    def _gen(self):
        # Per-mode noise levels.
        # 各模式的噪声强度。
        n, fs = self.n, self.fs
        rows = []
        st_lin = {"resting": 0.025, "tapping": 0.06,
                  "scrolling": 0.05, "walking": 0.08}[self.mode]
        st_gyro = {"resting": 0.008, "tapping": 0.02,
                   "scrolling": 0.02, "walking": 0.05}[self.mode]
        walk_step_freq = 1.7 + self.rng.random() * 0.5
        tap_every = 0.18 + self.rng.random() * 0.3

        for i in range(n):
            t = i / fs
            x, y, z = self._base
            # Low-frequency breathing / environment vibration + high-freq noise.
            # 低频呼吸 / 环境振动 + 高频噪声。
            vib = (math.sin(2 * math.pi * (1.8 + self.rng.random()) * t) * 0.015
                   + self.rng.gauss(0.0, st_lin))
            lin = [x * 0.02 + vib, y * 0.02 + vib * 0.8, vib]
            gyr = [self.rng.gauss(0.0, st_gyro),
                   self.rng.gauss(0.0, st_gyro),
                   self.rng.gauss(0.0, st_gyro)]

            if self.mode == "walking":
                # Walking: two impacts per step (heel strike + push off).
                # 步行：每步两连击（着地 + 蹬地）。
                ph = t * walk_step_freq
                frac = ph - int(ph)
                impact = (_smooth_pulse(frac, 0.15) * 0.32
                          + _smooth_pulse(frac, 0.55) * 0.18)
                lin[2] += impact
                gyr[0] += self.rng.gauss(0.0, 0.02) + impact * 0.05
            elif self.mode == "tapping":
                # Tapping: head impact + rebound.
                # 点按：头部冲击 + 回弹。
                ph = (t % tap_every) / tap_every
                tap = _smooth_pulse(ph, 0.3, 0.05) * 0.45
                lin[0] += tap * 0.5
                lin[2] += tap
                gyr[1] += self.rng.gauss(0.0, 0.02) + tap * 0.1
            elif self.mode == "scrolling":
                # Scrolling: y-axis translation + slight gyro rotation.
                # 滑动：y 轴平移微冲 + 陀螺轻微转动。
                ph = (t % 0.9) / 0.9
                sw = _smooth_pulse(ph, 0.8, 0.18) * 0.10
                lin[1] += sw
                gyr[2] += sw * 0.5

            acc = [x + lin[0], y + lin[1], z + lin[2]]
            mag = [30.0 + self.rng.gauss(0.0, 0.8),
                   -20.0 + self.rng.gauss(0.0, 0.8),
                   -45.0 + self.rng.gauss(0.0, 0.8)]
            rows.append({
                "t": round(t, 4),
                "acc": [round(v, 5) for v in acc],
                "lin": [round(v, 5) for v in lin],
                "gyro": [round(v, 5) for v in gyr],
                "mag": [round(v, 5) for v in mag],
            })
        return rows

    def write_csv(self, path: str) -> None:
        # Export 13 columns: t + 3-axis acc / lin / gyro / mag.
        # 导出 13 列：t + 三轴 acc / lin / gyro / mag。
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["t", "acc_x", "acc_y", "acc_z",
                        "lin_x", "lin_y", "lin_z",
                        "gyro_x", "gyro_y", "gyro_z",
                        "mag_x", "mag_y", "mag_z"])
            for r in self.rows:
                w.writerow([r["t"], *r["acc"], *r["lin"], *r["gyro"], *r["mag"]])


class Sensors:
    """Sensors module facade: generate + stats + deadness detection.

    传感器模块门面：生成序列 + 统计 + 死寂检测。
    """

    def __init__(self, config: dict | None = None, rng: random.Random | None = None):
        # Instance-level rng; never touch global random.
        # 实例级 rng；不触碰全局 random。
        self.rng = rng or random.Random()
        c = config or {}
        self.fs = float(c.get("fs", 100.0))
        self.duration = float(c.get("duration", 5.0))
        self.mode = str(c.get("mode", "resting"))
        self.dead_std = float(c.get("dead_std_threshold", 0.02))
        self.gyro_dead_std = float(c.get("gyro_dead_std", 0.001))
        self.dead_zero_ratio_max = float(c.get("dead_zero_ratio_max", 0.9))

    def generate(self, mode: str | None = None, fs: float | None = None,
                 duration: float | None = None) -> list[dict]:
        # Build a SensorProfile and return its rows.
        # 构造 SensorProfile 并返回序列。
        p = SensorProfile(fs=fs if fs is not None else self.fs,
                          duration=duration if duration is not None else self.duration,
                          mode=mode or self.mode,
                          rng=self.rng)
        return p.rows

    def stats(self, rows: list[dict]) -> dict:
        # Per-axis std + zero-change ratio + dead_signals count.
        # 各轴 std + 零变化比例 + dead_signals 计数。
        ax = [r["acc"][0] for r in rows]
        ay = [r["acc"][1] for r in rows]
        az = [r["acc"][2] for r in rows]
        gx = [r["gyro"][0] for r in rows]
        gy = [r["gyro"][1] for r in rows]
        gz = [r["gyro"][2] for r in rows]
        out = {}
        dead_signals = 0
        for name, ch, thr in (("acc_x", ax, self.dead_std),
                              ("acc_y", ay, self.dead_std),
                              ("acc_z", az, self.dead_std),
                              ("gyro_x", gx, self.gyro_dead_std),
                              ("gyro_y", gy, self.gyro_dead_std),
                              ("gyro_z", gz, self.gyro_dead_std)):
            std = _axis_std(ch)
            zr = _zero_change_ratio(ch)
            out[f"{name}_std"] = std
            out[f"{name}_zero"] = zr
            if std < thr or zr > self.dead_zero_ratio_max:
                dead_signals += 1
        out["dead_signals"] = dead_signals
        return out

    def is_dead(self, rows: list[dict], dead_signal_limit: int = 0) -> bool:
        # A sequence is "dead" if more axes than the limit look dead.
        # 超过限定数量的轴被判「死寂」即整体判死寂。
        return self.stats(rows)["dead_signals"] > dead_signal_limit
