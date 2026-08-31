# 文档语言维护方针

## 正本与派生文档

- README.md 和 docs/ 下的编号文件是日文技术正本。
- README.en.md 与 README.zh-Hans.md 是从正本展开的公开概要。
- 数值、需求 ID、命令、文件名和证据边界必须在各语言中保持一致。
- 非完整翻译的文档必须标明为概要或“日文正本链接”，不能让读者误以为已经完整翻译。

## 更新流程

1. 先在日文正本中加入规格、证据和限制。
2. 将同一变更同步到英文和简体中文概要、图示及证据表。
3. 修改数值时检查机器可读 JSON 报告及其链接。
4. 检查语言链接、CITATION.cff 和文档许可覆盖范围。

该结构避免维护三份相互独立的详细规格，同时保留分离的公开语言入口。

## 覆盖范围

| 层级 | 日文 | English | 简体中文 |
|---|---|---|---|
| 公开入口 | README.md | README.en.md | README.zh-Hans.md |
| 详细规格 | docs/*.md | docs/README.en.md 引导至正本 | docs/README.zh-Hans.md 引导至正本 |
| 概念说明 | docs/concepts/*.md | 带 .en.md 后缀的文件 | 带 .zh-Hans.md 后缀的文件 |
| 验证结果 | VALIDATION.md／evidence | VALIDATION.en.md | VALIDATION.zh-Hans.md |
