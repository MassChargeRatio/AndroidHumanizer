# -*- coding: utf-8 -*-
import random
import tempfile
import os

from touch_humanization.sensors import Sensors, SensorProfile


def test_all_modes_alive():
    s = Sensors(rng=random.Random(42))
    for mode in ("resting", "walking", "tapping", "scrolling"):
        rows = s.generate(mode=mode, fs=100.0, duration=2.0)
        assert not s.is_dead(rows), mode


def test_dead_data_detected():
    s = Sensors(rng=random.Random(0))
    dead = [{"t": i * 0.01, "acc": [0.0, 0.0, 9.8], "lin": [0, 0, 0],
             "gyro": [0.0, 0.0, 0.0], "mag": [0.0, 0.0, 0.0]} for i in range(200)]
    assert s.is_dead(dead) is True


def test_reproducible():
    a = Sensors(rng=random.Random(7)).generate(mode="walking", fs=50, duration=1.0)
    b = Sensors(rng=random.Random(7)).generate(mode="walking", fs=50, duration=1.0)
    assert a == b


def test_csv_export():
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "s.csv")
        SensorProfile(fs=50, duration=1.0, mode="resting",
                      rng=random.Random(1)).write_csv(p)
        with open(p, encoding="utf-8") as f:
            head = f.readline().strip()
        assert head.startswith("t,acc_x")
        assert os.path.getsize(p) > 100
