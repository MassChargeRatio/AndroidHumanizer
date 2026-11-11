# 许可证审计（阶段 0）

## 审计对象

| 对象 | 路径 | 状态 |
|---|---|---|
| 原仓根目录 | `AndroidAutopilot/`（交接包根） | 已核对文件索引 |
| 待移植源码 | `human_trajectory.py` | 已取得完整源码 |
| 五个核心函数 | `_bezier3` / `_control_points` / `_smoothstep` / `_ease_out_quad` / `_gauss` | 已逐一定位 |

## 原仓根目录许可证文件

根据交接包 `ALL-IN-ONE-WITH-SOURCE.md` 的**文件索引**，原仓根目录**不存在**以下文件：

- `LICENSE`
- `COPYING`
- `NOTICE`
- `LICENSE.txt` / `LICENSE.md` 等变体

**结论**：原仓本身**未声明项目级许可证**。这意味着：

1. 原仓作者对其代码保留全部权利（默认版权），本项目**不能直接复制原仓代码**并声称 MIT。
2. 本项目对 `human_trajectory.py` 的处理方式是**算法移植**，不是代码复制（见 `upstream-trace.md`）。
3. 本项目以 MIT 发布时，**不包含**原仓代码本身，仅包含独立实现的等价算法。

## 上游算法许可证

`human_trajectory.py` 的 docstring 明确引用了三个上游项目作为算法参考：

| 上游项目 | 许可证 | 与本项目 MIT 兼容性 | 引用范围 |
|---|---|---|---|
| pyclick | MIT | 兼容 | 伯恩斯坦贝塞尔 + 高斯失真 |
| ghost-cursor 原版 | ISC | 兼容 | Fitts 步数 + 过冲修正 |
| bezier-mouse-js | MIT | 兼容 | 三次贝塞尔 |

**三者的许可证均允许在保留版权声明的前提下自由使用、修改、再分发**（MIT 与 ISC 均为宽松许可证）。

## 本项目对上游的处理方式

| 处理 | 说明 |
|---|---|
| 算法参考 | 读取上游算法思想，不复制上游代码 |
| 独立实现 | 在 `android_humanizer/kinematics/trajectory.py` 中以纯 Python 重写 |
| 函数命名 | 使用本项目自有的函数名（`_bezier3` / `_control_points` / `_smoothstep` / `_ease_out_quad` / `_gauss`），与原仓同名但非复制 |
| 版权声明 | 在 `LICENSE` 末尾保留对三个上游项目的致谢，并声明其原始版权归属 |

## 结论

- 原仓无许可证文件 → **不能直接复制原仓代码**，本项目采用算法移植。
- 三个上游项目许可证均为 MIT/ISC → **与 MIT 兼容**。
- 本项目以 MIT 发布 **不阻塞**。
- 建议：首次 `twine upload` 前，在 `README.md` 的"上游参考"节再次确认三个上游仓库的 `LICENSE` 文件仍然存在且未被改版（上游可能变更许可证，概率极低但需核实）。

## 待办

- [ ] 首次发布前复核 pyclick / ghost-cursor / bezier-mouse-js 的当前 `LICENSE` 文件
- [ ] 确认 `LICENSE` 中的上游致谢段落与实际使用的算法范围一致
