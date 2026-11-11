# -*- coding: utf-8 -*-
# Kinematics unit tests (no device needed).
# kinematics 单元测试（无需设备）。
import random

import pytest

from touch_humanization.kinematics import Kinematics
from touch_humanization.kinematics.trajectory import (
    _bezier3, _control_points, _smoothstep, _ease_out_quad, _gauss,
)


def test_bezier3_endpoints():
    # Bezier must return p0 at t=0 and p3 at t=1.
    # 贝塞尔在 t=0 返回 p0，在 t=1 返回 p3。
    p0, p1, p2, p3 = (0, 0), (1, 2), (3, 2), (4, 0)
    assert _bezier3(p0, p1, p2, p3, 0.0) == p0
    assert _bezier3(p0, p1, p2, p3, 1.0) == p3


def test_smoothstep_bounds_and_midpoint():
    # Smoothstep boundary and midpoint values.
    # smoothstep 的边界与中点值。
    assert _smoothstep(0) == 0
    assert _smoothstep(1) == 1
    assert abs(_smoothstep(0.5) - 0.5) < 1e-9


def test_ease_out_quad_bounds():
    # EaseOutQuad boundary values.
    # easeOutQuad 的边界值。
    assert _ease_out_quad(0) == 0
    assert _ease_out_quad(1) == 1


def test_gauss_reproducible():
    # Same seed -> same gaussian sample.
    # 同 seed -> 同一高斯采样值。
    a = _gauss(random.Random(42), 0, 1)
    b = _gauss(random.Random(42), 0, 1)
    assert a == b


def test_control_points_symmetric_origin():
    # Control points for a horizontal move: perpendicular offset must be non-zero.
    # 水平移动的控制点：垂直偏移必须非零。
    rng = random.Random(1)
    p1, p2 = _control_points(rng, (0, 0), (100, 0), 100.0, 0.12)
    assert p1[0] == p2[0] == 50.0
    assert abs(p1[1]) > 0
    assert abs(p2[1]) > 0


def test_generate_exact_end_and_length():
    # Exact end and consistent lengths.
    # 终点精确、长度一致。
    h = Kinematics(rng=random.Random(7))
    g = h.generate((100, 1800), (900, 400))
    assert g.points[0] == (100, 1800)
    assert g.points[-1] == (900, 400)
    assert len(g.intervals) == len(g.points) - 1
    assert g.duration == pytest.approx(sum(g.intervals), rel=1e-6)


def test_generate_reproducible():
    # Same seed -> identical trajectory.
    # 同 seed -> 轨迹完全一致。
    a = Kinematics(rng=random.Random(3)).generate((0, 0), (500, 500))
    b = Kinematics(rng=random.Random(3)).generate((0, 0), (500, 500))
    assert a.points == b.points
    assert a.intervals == b.intervals


def test_generate_fitts_steps_monotonic():
    # Longer distance -> more steps (Fitts), capped by steps_max.
    # 距离越远步数越多（Fitts），受 steps_max 上限约束。
    h = Kinematics(rng=random.Random(0))
    short = h.generate((0, 0), (100, 0))
    long = h.generate((0, 0), (2000, 0))
    assert short.steps < long.steps
    assert long.steps <= h.steps_max + 1


def test_slider_monotonic_and_exact():
    # Slider mode: monotonic x and exact end.
    # 滑块模式：x 单调递增、终点精确。
    h = Kinematics(rng=random.Random(11))
    g = h.generate((80, 1500), (1200, 1500), for_slider=True)
    assert g.for_slider is True
    assert g.points[-1] == (1200, 1500)
    xs = [p[0] for p in g.points]
    assert all(xs[i] <= xs[i + 1] + 1 for i in range(len(xs) - 1))


def test_disabled_returns_straight_line():
    # Disabled kinematics: straight line with 8 points.
    # kinematics 禁用时：8 点直线。
    h = Kinematics({"enabled": False}, rng=random.Random(0))
    g = h.generate((0, 0), (80, 80))
    assert len(g.points) == 8
    assert g.points[-1] == (80, 80)
