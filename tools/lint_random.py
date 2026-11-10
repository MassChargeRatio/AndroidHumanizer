#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""禁止 random.seed / 全局 random.* / numpy.random 的 CI lint。

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

BANNED = [
    (re.compile(r"\brandom\.seed\s*\("), "禁止 random.seed()"),
    (re.compile(r"\brandom\.(random|uniform|gauss|choice|choices|randint|"
                r"randrange|shuffle|sample|betavariate|expovariate|"
                r"gammavariate|lognormvariate|normalvariate|triangular|"
                r"vonmisesvariate|paretovariate|weibullvariate)\s*\("),
     "禁止全局 random.*（请用实例 rng.xxx()）"),
    (re.compile(r"\bnp\.random\b"), "禁止 numpy.random（本项目零依赖）"),
    (re.compile(r"\bnumpy\.random\b"), "禁止 numpy.random（本项目零依赖）"),
]

ALLOWED = [
    re.compile(r"\brandom\.Random\s*\("),
]


def scan(path: Path) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits
    for i, line in enumerate(text.splitlines(), 1):
        if any(a.search(line) for a in ALLOWED):
            # 同一行可能同时含 Random( 与别的调用；先剥掉允许片段再判
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
    ap = argparse.ArgumentParser(description="禁止 random.seed / 全局 random.* / numpy.random")
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
        print(f"\n发现 {total} 处违规。")
        return 1
    print("OK  未发现 random.seed / 全局 random.* / numpy.random。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
