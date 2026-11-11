# 依赖许可证清单（阶段 0）

## 运行时依赖

**无。** `touch_humanization` 仅使用 Python 标准库（`random`、`math`、`csv`、`json`、`http.server`、`urllib`、`statistics`、`dataclasses`、`argparse`、`webbrowser`、`posixpath`、`io`、`os`、`sys`）。

**依据**：`pyproject.toml` 的 `[project]` 节无 `dependencies` 字段；源码 `import` 全部来自标准库。

## 开发/测试依赖

| 包 | 版本约束 | 许可证 | 与本项目 MIT 兼容性 | 用途 |
|---|---|---|---|---|
| `pytest` | `>=7` | MIT | 兼容 | 测试运行器 |
| `setuptools` | `>=68` | MIT | 兼容 | 构建后端（`build-system.requires`） |
| `wheel` | 任意 | MIT | 兼容 | 构建后端 |

**说明**：`pyyaml` 曾出现在早期草稿的 dev 依赖里，但本项目不解析 YAML、不读取 `config.yaml`（配置以 dict 传入 `Humanizer`），故已从 `pyproject.toml` 删除。

## 传递依赖

`pytest` 的传递依赖（如 `pluggy`、`iniconfig`、`packaging`、`tomli`）均为 MIT/BSD/Apache-2.0 类宽松许可证，与 MIT 兼容。这些依赖**不随本包分发**（仅开发环境安装），不进入 PyPI wheel 的 `Requires-Dist`。

## 结论

- 运行时依赖：**0 个**，无任何许可证兼容性风险。
- 开发依赖：全部 MIT，与 MIT 兼容。
- 不存在 GPL/AGPL/LGPL 等 copyleft 依赖。
- **不阻塞** `touch-humanization` 以 MIT 发布。
