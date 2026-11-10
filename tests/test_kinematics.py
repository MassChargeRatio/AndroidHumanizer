# -*- coding: utf-8 -*-
import math
import random

import pytest

from touch_humanization.kinematics import Kinematics
from touch_humanization.kinematics.trajectory import (
    _bezier3, _control_points, _smoothstep, _ease_out_quad, _gauss,
)


def test_bezier3_endpoints():
    p0, p1, p2, p3 = (0, 0), (1, 2), (3, 2), (4, 0)
    assert _bezier3(p0, p1, p2, p3, 0.0) == p0
    assert _bezier3(p0, p1, p2, p3, 1.0) == p3


def test_smoothstep_bounds_and_midpoint():
    assert _smoothstep(0) == 0
    assert _smoothstep(1) == 1
    assert abs(_smoothstep(0.5) - 0.5) < 1e-9


def test_ease_out_quad_bounds():
    assert _ease_out_quad(0) == 0
    assert _ease_out_quad(1) == 1


def test_gauss_reproducible():
    a = _gauss(random.Random(42), 0, 1)
    b = _gauss(random.Random(42), 0, 1)
    assert a == b


def test_control_points_symmetric_origin():
    rng = random.Random(1)
    p1, p2 = _control_points(rng, (0, 0), (100, 0), 100.0, 0.12)
    assert p1[0] == p2[0] == 50.0
    assert abs(p1[1]) > 0
    assert abs(p2[1]) > 0


def test_generate_exact_end_and_length():
    h = Kinematics(rng=random.Random(7))
    g = h.generate((100, 1800), (900, 400))
    assert g.points[0] == (100, 1800)
    assert g.points[-1] == (900, 400)
    assert len(g.intervals) == len(g.points) - 1
    assert g.duration == pytest.approx(sum(g.intervals), rel=1e-6)


def test_generate_reproducible():
    a = Kinematics(rng=random.Random(3)).generate((0, 0), (500, 500))
    b = Kinematics(rng=random.Random(3)).generate((0, 0), (500, 500))
    assert a.points == b.points
    assert a.intervals == b.intervals


def test_generate_fitts_steps_monotonic():
    h = Kinematics(rng=random.Random(0))
    short = h.generate((0, 0), (100, 0))
    long = h.generate((0, 0), (2000, 0))
    assert short.steps < long.steps
    assert long.steps <= h.steps_max + 1  # exact_end 不增点


def test_slider_monotonic_and_exact():
    h = Kinematics(rng=random.Random(11))
    g = h.generate((80, 1500), (1200, 1500), for_slider=True)
    assert g.for_slider is True
    assert g.points[-1] == (1200, 1500)
    xs = [p[0] for p in g.points]
    assert all(xs[i] <= xs[i + 1] + 1 for i in range(len(xs) - 1))


def test_disabled_returns_straight_line():
    h = Kinematics({"enabled": False}, rng=random.Random(0))
    g = h.generate((0, 0), (80, 80))
    assert len(g.points) == 8
    assert g.points[-1] == (80, 80)
