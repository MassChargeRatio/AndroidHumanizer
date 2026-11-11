#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CI lint: forbid random.seed / global random.* / numpy.random.

Allowed:
  * random.Random(...) instantiation
  * instance method calls like rng.xxx() / self.rng.xxx()

Forbidden:
  * random.seed(...)
  * module-level calls like random.random() / random.uniform(...) / random.gauss(...)
  * np.random / numpy.random

Exit code: 0 = clean; 1 = violations found.

CI lint：禁止 random.seed / 全局 random.* / numpy.random。

允许：
  * random.Random(...) 实例化
  * rng.xxx() / self.rng.xxx() 实例方法调用

禁止：
  * random.seed(...)
  * random.random() / random.uniform(...) / random.gauss(...) 等模块级调用
  * np.random / numpy.random

退出码：0 干净；1 发现问题。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Banned patterns and their explanations.
# 禁止模式与对应说明。
BANNED = [
    (re.compile(r"\brandom\.seed\s*\("),
     "forbid random.seed() / 禁止 random.seed()"),
    (re.compile(r"\brandom\.(random|uniform|gauss|choice|choices|randint|"
                r"randrange|shuffle|sample|betavariate|expovariate|"
                r"gammavariate|lognormvariate|normalvariate|triangular|"
                r"vonmisesvariate|paretovariate|weibullvariate)\s*\("),
     "forbid global random.* (use instance rng.xxx()) / 禁止全局 random.*（请用实例 rng.xxx()）"),
    (re.compile(r"\bnp\.random\b"),
     "forbid numpy.random (zero-dependency project) / 禁止 numpy.random（本项目零依赖）"),
    (re.compile(r"\bnumpy\.random\b"),
     "forbid numpy.random (zero-dependency project) / 禁止 numpy.random（本项目零依赖）"),
]

# Explicitly allowed patterns (skipped when they appear on the same line).
# 显式允许的模式（同行出现时跳过）。
ALLOWED = [
    re.compile(r"\brandom\.Random\s*\("),
]


def scan(path: Path) -> list:
    # Return [(line_no, reason, line_text), ...] for the given file.
    # 返回给定文件的 [(行号, 原因, 行文本), ...]。
    hits: list = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits
    for i, line in enumerate(text.splitlines(), 1):
        # If the line contains an allowed pattern, strip it before checking bans.
        # 若该行含允许模式（如 random.Random(），先剥离再判禁止模式，
        # 避免同一行同时含 Random( 与别的调用时漏报。
        if any(a.search(line) for a in ALLOWED):
            stripped = line
            for a in ALLOWED:
                stripped = a.sub("", stripped)
            if any(b.search(stripped) for b, _ in BANNED):
                for b, why in BANNED:
                    if b.search(stripped):
                        hits.append((i, why, line.strip()))
            continue
        for b, why in BANNED:
            if b.search(line):
                hits.append((i, why, line.strip()))
                break
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Forbid random.seed / global random.* / numpy.random")
    ap.add_argument("paths", nargs="*", default=["touch_humanization"])
    args = ap.parse_args(argv)

    total = 0
    for root in args.paths:
        p = Path(root)
        files = [p] if p.is_file() else sorted(p.rglob("*.py"))
        for f in files:
            for lineno, why, line in scan(f):
                total += 1
                print(f"{f}:{lineno}: {why}\n    {line}")
    if total:
        print(f"\n发现 {total} 处违规。/ {total} violation(s) found.")
        return 1
    print("OK  未发现 random.seed / 全局 random.* / numpy.random。"
          " / no forbidden random usage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
