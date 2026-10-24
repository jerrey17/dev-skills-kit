# tapd-wiki-publish

把技术方案 Markdown 推到 TAPD Wiki，供测试和产品评审。首次创建，之后按 wiki id 更新。

## 何时使用

技术方案自检通过后，或用户要求把方案推到 Wiki。

## 输入

方案文件路径、TAPD workspace id、父 wiki 或已有 wiki id。token 从命令行参数、本地配置或环境变量读取。

## 产出

Wiki 页面，以及本地状态文件里的 wiki 地址和版本。

大文档走 `scripts/push_wiki.py`，避免把全文塞进对话。详细步骤见 `SKILL.md`。
