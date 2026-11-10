# -*- coding: utf-8 -*-
"""Humanizer 门面：单一随机流贯穿 kinematics / timing / sensors。"""
from __future__ import annotations

import random
import time

from .config import merge_config
from .kinematics import Gesture, Kinematics
from .sensors import Sensors
from .timing import Timing

__all__ = ["Humanizer", "Gesture"]


class Humanizer:
    """拟人化门面。

    - 传 seed 时内部创建**一个** random.Random，三个子模块共享它（单一流）。
    - 不传 seed 时同样创建一个实例流，不污染全局 random。
    - 三个子模块也可单独使用（各自持有实例 rng）。
    """

    def __init__(self, config: dict | None = None, seed: int | None = None):
        self.config = merge_config(config)
        self.rng = random.Random(seed)
        self.kinematics = Kinematics(self.config["kinematics"], rng=self.rng)
        self.timing = Timing(self.config["timing"], rng=self.rng)
        self.sensors = Sensors(self.config["sensors"], rng=self.rng)

    def gesture(self, start, end, *, for_slider: bool = False,
                exact_end: bool = True) -> Gesture:
        return self.kinematics.generate(start, end,
                                        for_slider=for_slider,
                                        exact_end=exact_end)

    def delay(self) -> float:
        v = self.timing.delay_between_actions()
        time.sleep(v)
        return v

    def think(self) -> float:
        v = self.timing.think()
        time.sleep(v)
        return v

    def after_open(self) -> float:
        v = self.timing.after_open()
        time.sleep(v)
        return v

    def start_wait(self) -> float:
        return self.timing.start_wait()

    def in_wake_window(self, now=None) -> bool:
        return self.timing.in_wake_window(now)

    def tap(self) -> float | None:
        return self.timing.tap()

    def captcha_cooldown(self) -> float:
        return self.timing.captcha_cooldown()
