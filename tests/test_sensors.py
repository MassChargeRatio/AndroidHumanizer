# -*- coding: utf-8 -*-
# Sensors unit tests.
# sensors 单元测试。
import os
import random
import tempfile

from touch_humanization.sensors import Sensors, SensorProfile


def test_all_modes_alive():
    # All four modes should look "alive" (not dead).
    # 四种模式都应判定为「活着」（非死寂）。
    s = Sensors(rng=random.Random(42))
    for mode in ("resting", "walking", "tapping", "scrolling"):
        rows = s.generate(mode=mode, fs=100.0, duration=2.0)
        assert not s.is_dead(rows), mode


def test_dead_data_detected():
    # A constant sequence must be detected as dead.
    # 完全恒定的序列必须判为死寂。
    s = Sensors(rng=random.Random(0))
    dead = [{"t": i * 0.01, "acc": [0.0, 0.0, 9.8], "lin": [0, 0, 0],
             "gyro": [0.0, 0.0, 0.0], "mag": [0.0, 0.0, 0.0]} for i in range(200)]
    assert s.is_dead(dead) is True


def test_reproducible():
    # Same seed -> identical sequence.
    # 同 seed -> 序列一致。
    a = Sensors(rng=random.Random(7)).generate(mode="walking", fs=50, duration=1.0)
    b = Sensors(rng=random.Random(7)).generate(mode="walking", fs=50, duration=1.0)
    assert a == b


def test_csv_export():
    # CSV export writes a valid header and has content.
    # CSV 导出写出合法表头且内容非空。
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "s.csv")
        SensorProfile(fs=50, duration=1.0, mode="resting",
                      rng=random.Random(1)).write_csv(p)
        with open(p, encoding="utf-8") as f:
            head = f.readline().strip()
        assert head.startswith("t,acc_x")
        assert os.path.getsize(p) > 100
