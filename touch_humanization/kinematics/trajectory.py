# -*- coding: utf-8 -*-
"""Human gesture trajectory generation.

Core algorithms reference:
  * pyclick (MIT)          - Bernstein bezier + Gaussian distortion
  * bezier-mouse-js (MIT)  - cubic bezier
  * ghost-cursor (ISC)     - Fitts steps + overshoot correction

The five core functions audited by the phase-0 upstream trace:
  _bezier3 / _control_points / _smoothstep / _ease_out_quad / _gauss

All randomness goes through the instance-level rng; global random.* is forbidden.

人类手势轨迹生成。

核心算法参考：
  * pyclick（MIT）         —— 伯恩斯坦贝塞尔 + 高斯失真
  * bezier-mouse-js（MIT） —— 三次贝塞尔
  * ghost-cursor（ISC）    —— Fitts 步数 + 过冲修正

五个核心函数（阶段 0 上游溯源对象）：
  _bezier3 / _control_points / _smoothstep / _ease_out_quad / _gauss

所有随机消费走实例级 rng，禁止全局 random.*。
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

__all__ = [
    "Gesture",
    "Kinematics",
    "_bezier3",
    "_control_points",
    "_smoothstep",
    "_ease_out_quad",
    "_gauss",
]


def _clamp(v: float, lo: float, hi: float) -> float:
    # Clamp helper.
    # 区间钳制辅助函数。
    return max(lo, min(hi, v))


def _bezier3(p0, p1, p2, p3, t: float):
    """Sample a point on a cubic bezier curve.

    三次贝塞尔曲线采样。
    """
    u = 1.0 - t
    x = (u ** 3) * p0[0] + 3 * (u ** 2) * t * p1[0] + 3 * u * (t ** 2) * p2[0] + (t ** 3) * p3[0]
    y = (u ** 3) * p0[1] + 3 * (u ** 2) * t * p1[1] + 3 * u * (t ** 2) * p2[1] + (t ** 3) * p3[1]
    return (x, y)


def _smoothstep(t: float) -> float:
    """Slow-fast-slow speed profile: 3t^2 - 2t^3.

    慢-快-慢速度轮廓：3t^2 - 2t^3。
    """
    t = _clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _ease_out_quad(t: float) -> float:
    """easeOutQuad: 1 - (1-t)^2.

    easeOutQuad：1 - (1-t)^2。
    """
    t = _clamp(t, 0.0, 1.0)
    u = 1.0 - t
    return 1.0 - u * u


def _gauss(rng: random.Random, mu: float = 0.0, sigma: float = 1.0) -> float:
    """Box-Muller Gaussian sample (zero numpy dependency).

    Box-Muller 高斯采样（零 numpy 依赖）。
    """
    u1 = rng.random()
    if u1 < 1e-12:
        u1 = 1e-12
    u2 = rng.random()
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return mu + sigma * z


def _control_points(rng: random.Random, start, end, dist: float,
                    perpendicular_ratio: float):
    """Cubic bezier control points: one-sided offset perpendicular to the main direction.

    三次贝塞尔控制点：沿垂直于主方向的单侧随机偏移。
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if dist < 1e-6:
        return start, end
    # Unit normal vector.
    # 单位法向量。
    nx, ny = -dy / dist, dx / dist
    # Random side (left or right).
    # 随机取正/负侧。
    side = 1.0 if rng.random() < 0.5 else -1.0
    amp = dist * perpendicular_ratio * rng.uniform(0.5, 1.4)
    mx, my = (start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0
    p1 = (mx + nx * side * amp, my + ny * side * amp)
    p2 = (mx + nx * side * amp * rng.uniform(0.5, 1.2),
          my + ny * side * amp * rng.uniform(0.5, 1.2))
    return p1, p2


@dataclass(frozen=True)
class Gesture:
    """A human gesture trajectory.

    points    : integer point sequence, len >= 2
    intervals : sleep seconds between adjacent points, len == len(points) - 1
    duration  : total duration in seconds
    distance  : straight-line distance between start and end
    steps     : number of sampled points
    for_slider: whether this is a slider-drag trajectory

    一条人类手势轨迹。

    points    : 整数坐标点序列，长度 >= 2
    intervals : 每两点之间的睡眠秒数，长度 == len(points) - 1
    duration  : 总时长（秒）
    distance  : 起终点直线距离
    steps     : 采样点数
    for_slider: 是否滑块拖拽模式
    """
    points: tuple[tuple[int, int], ...]
    intervals: tuple[float, ...]
    duration: float
    distance: float
    steps: int
    for_slider: bool

    def as_dict(self) -> dict:
        # Serializable view for Web UI.
        # 供 Web UI 使用的可序列化视图。
        return {
            "points": [list(p) for p in self.points],
            "intervals": list(self.intervals),
            "duration": self.duration,
            "distance": self.distance,
            "steps": self.steps,
            "for_slider": self.for_slider,
        }


class Kinematics:
    """Human gesture trajectory generator.

    人类手势轨迹生成器。
    """

    def __init__(self, config: dict | None = None, rng: random.Random | None = None):
        # Instance-level rng; never touch global random.
        # 实例级 rng；不触碰全局 random。
        self.rng = rng or random.Random()
        c = config or {}
        self.enabled = bool(c.get("enabled", True))
        self.steps_min = int(c.get("steps_min", 20))
        self.steps_max = int(c.get("steps_max", 60))
        self.px_per_step = float(c.get("px_per_step", 15.0))
        self.duration_per_px = float(c.get("duration_per_px", 0.0007))
        self.duration_min = float(c.get("duration_min", 0.3))
        self.duration_max = float(c.get("duration_max", 1.5))
        self.perpendicular_ratio = float(c.get("perpendicular_ratio", 0.12))
        self.use_ease_in_out = bool(c.get("use_ease_in_out", True))
        self.jitter_sigma = float(c.get("jitter_sigma", 1.2))
        self.jitter_tail_fraction = float(c.get("jitter_tail_fraction", 0.25))
        self.overshoot_prob = float(c.get("overshoot_prob", 0.25))
        self.overshoot_ratio = float(c.get("overshoot_ratio", 0.06))

    def generate(self, start, end, *, for_slider: bool = False,
                 exact_end: bool = True) -> Gesture:
        """Generate one human gesture trajectory.

        生成一条人类手势轨迹。
        """
        p0 = (float(start[0]), float(start[1]))
        p3 = (float(end[0]), float(end[1]))
        dx = p3[0] - p0[0]
        dy = p3[1] - p0[1]
        dist = math.hypot(dx, dy)

        # Disabled: fall back to a straight line.
        # 禁用时：退化为直线。
        if not self.enabled:
            n = 8
            pts = [(p0[0] + dx * i / (n - 1), p0[1] + dy * i / (n - 1))
                   for i in range(n)]
            pts[-1] = p3
            intervals = [0.02] * (n - 1)
            return Gesture(tuple((int(round(x)), int(round(y))) for x, y in pts),
                           tuple(intervals), sum(intervals), dist, n, for_slider)

        # Degenerate distance: just two points. The slider branch does not
        # apply below 1 px, so always report a plain (non-slider) gesture
        # to avoid returning slider=True without slider semantics.
        # 距离过短：只返回两个点。极短距离下滑块分支无意义，
        # 一律按普通两点手势返回，避免出现 slider=True 却无滑块语义的歧义。
        if dist < 1.0:
            pts = [(int(round(p0[0])), int(round(p0[1]))),
                   (int(round(p3[0])), int(round(p3[1])))]
            return Gesture(tuple(pts), (0.02,), 0.02, dist, 2, False)

        # Fitts-style step count and duration.
        # Fitts 风格步数与总时长。
        steps = int(_clamp(dist / self.px_per_step, self.steps_min, self.steps_max))
        duration = _clamp(dist * self.duration_per_px,
                          self.duration_min, self.duration_max)

        # Slider drag uses its own branch.
        # 滑块拖拽走独立分支。
        if for_slider:
            return self._slider(p0, p3, steps, duration, dist)

        # Overshoot: pass the target then pull back.
        # 过冲：先越过终点再回拉。
        overshoot = 0.0
        if self.rng.random() < self.overshoot_prob:
            overshoot = dist * self.overshoot_ratio * self.rng.uniform(0.6, 1.2)
        if overshoot > 0:
            s = overshoot / dist
            p3o = (p0[0] + dx * (1 + s), p0[1] + dy * (1 + s))
        else:
            p3o = p3

        p1, p2 = _control_points(self.rng, p0, p3o, dist + overshoot,
                                 self.perpendicular_ratio)
        pts = [_bezier3(p0, p1, p2, p3o, i / (steps - 1)) for i in range(steps)]

        # Append pull-back points after overshoot.
        # 过冲后追加回拉点。
        if overshoot > 0:
            back_n = max(3, steps // 6)
            for i in range(1, back_n + 1):
                f = 1.0 - i / back_n
                pts.append((p3[0] + (p3o[0] - p3[0]) * f,
                            p3[1] + (p3o[1] - p3[1]) * f))

        # Speed profile: smoothstep (slow-fast-slow) or easeOutQuad.
        # 速度轮廓：smoothstep（慢-快-慢）或 easeOutQuad。
        n = len(pts)
        if self.use_ease_in_out:
            ts = [_smoothstep(i / (n - 1)) for i in range(n)]
        else:
            ts = [_ease_out_quad(i / (n - 1)) for i in range(n)]
        intervals = []
        for i in range(1, n):
            dt = duration * (ts[i] - ts[i - 1])
            # Per-step jitter to avoid perfectly regular timing.
            # 每步随机扰动，避免完全规整的时序。
            dt *= self.rng.uniform(0.6, 1.4)
            intervals.append(dt)

        # Tail jitter: human finger tremor at the end of the move.
        # 末段微颤：动作结尾的手指生理抖动。
        if self.jitter_sigma > 0:
            tail_from = int(n * (1.0 - self.jitter_tail_fraction))
            for i in range(tail_from, n - 1):
                f = (i - tail_from) / max(1, (n - 1 - tail_from))
                sigma = self.jitter_sigma * (0.3 + 0.7 * f)
                pts[i] = (pts[i][0] + _gauss(self.rng, 0, sigma),
                          pts[i][1] + _gauss(self.rng, 0, sigma))

        # Force exact end and add a small "settle" delay.
        # 强制终点精确，并在末尾加一小段"落定"延迟。
        if exact_end:
            pts[-1] = p3
            intervals[-1] = intervals[-1] + self.rng.uniform(0.05, 0.2)

        ip = tuple((int(round(x)), int(round(y))) for x, y in pts)
        it = tuple(intervals)
        return Gesture(ip, it, sum(it), dist, len(ip), False)

    def _slider(self, p0, p3, steps: int, duration: float,
                dist: float) -> Gesture:
        """Slider drag: nearly pure horizontal, head/tail pinned, exact end.

        滑块拖拽：近乎纯水平、头尾贴轨道、终点精确。
        """
        dx = p3[0] - p0[0]
        n = max(2, steps)
        ts = [_smoothstep(i / (n - 1)) for i in range(n)]
        pts = []
        for i in range(n):
            x = p0[0] + dx * ts[i]
            # Tiny vertical jitter only in the middle; head/tail stay on track.
            # 仅中段有极小 y 抖动；头尾保持贴轨道。
            if 2 <= i <= n - 3:
                y = p0[1] + _gauss(self.rng, 0, 0.5)
            else:
                y = p0[1]
            pts.append((x, y))
        intervals = []
        for i in range(1, n):
            dt = duration * (ts[i] - ts[i - 1]) * self.rng.uniform(0.7, 1.3)
            intervals.append(dt)
        pts[-1] = p3
        ip = tuple((int(round(x)), int(round(y))) for x, y in pts)
        it = tuple(intervals)
        return Gesture(ip, it, sum(it), dist, len(ip), True)
