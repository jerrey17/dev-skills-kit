---
name: tapd-wiki-publish
description: 将技术方案 Markdown 推送到 TAPD Wiki 供测试/产品评审。首次创建，后续更新。独立调用，或由 dev-workflow 在技术方案自检通过后触发。
---

# TAPD Wiki 推送

## 定位

把 `workflow/{需求名}/03-技术方案.md`（或其他 Markdown 产物）推送到 TAPD Wiki 指定父模块下。
首次推送 → 走 `scripts/push_wiki.py`（不传 `--wiki-id`）；后续推送 → 同脚本（传 `--wiki-id`）。

## 大内容推送的根因

`mcp__tapd__update_wiki` 工具的 `markdown_description` 参数要走 Claude 输出 token。
单次技术方案文档通常 100~200KB，作为参数输出会触发 25000 token 上限被截断。
所以**默认走 `scripts/push_wiki.py` 脚本**：脚本直接读文件 + 直接 POST HTTP，不经过 Claude 输出 token。

阈值规则（配置在 `~/.claude/.tapd-wiki-config.json` 的 `large_content_threshold_kb`，默认 30KB）：

| 文件大小 | 推荐路径 | 原因 |
|---------|---------|------|
| < 30KB | `mcp__tapd__create_wiki` / `update_wiki` | 小内容无 token 截断风险，且 mcp 工具结果直接可见 |
| ≥ 30KB | `scripts/push_wiki.py` | 绕过 Claude 输出 token，稳定推送大文档 |

**判断不准时统一走脚本**，脚本对任意大小都能工作。

## 配置

配置文件：`~/.claude/.tapd-wiki-config.json`（权限 600）

```json
{
  "creator": "示例作者",
  "tapd_access_token": "<32位 hex token>",
  "tapd_api_base_url": "https://api.tapd.cn",
  "tapd_base_url": "https://www.tapd.cn",
  "large_content_threshold_kb": 30,
  "wiki_targets": [
    {
      "name": "示例项目",
      "project_root": "/path/to/project",
      "workspace_id": "100001",
      "parent_wiki_id": "11100001001026027"
    }
  ]
}
```

匹配规则：按 `current.md` 中「主项目」路径匹配 `wiki_targets[i].project_root`。
匹配失败 → 终止推送，提示用户在 `~/.claude/.tapd-wiki-config.json` 补充对应项目配置。

## Token 来源（fallback 链）

`scripts/push_wiki.py` 按以下优先级查找 token：

1. 命令行 `--token` 参数
2. `~/.claude/.tapd-wiki-config.json` 的 `tapd_access_token` 字段（推荐，填一次永久复用）
3. 环境变量 `TAPD_ACCESS_TOKEN`

任一来源取到即可。**推荐做法**：在配置文件填 `tapd_access_token`（已配权限 600），脚本自动读。不要从其他进程的环境变量里取 token。

## 状态文件

路径：`{project_root}/.claude/workflow/{需求名}/tapd-wiki.json`

```json
{
  "workspace_id": "100001",
  "parent_wiki_id": "11100001001026027",
  "wiki_id": "11100001001029900",
  "wiki_url": "https://www.tapd.cn/100001/markdown_wikis/show/#11100001001029900",
  "version_label": "v2.4.3",
  "last_pushed_at": "2026-07-29 17:25",
  "source_md_path": "/path/to/project/workflow/示例需求/03-技术方案.md",
  "source_md_mtime": 1785316268,
  "pushed_content_scope": "全文 v2.4.3"
}
```

脚本在推送成功后自动写状态文件，无需手动维护。

## current.md 索引

脚本在推送成功后自动追加/替换 `current.md` 中以 `- TAPD Wiki:` 开头的行（不存在则在 `- PR 链接` 行后插入）：

```
- TAPD Wiki: https://www.tapd.cn/100001/markdown_wikis/show/#11100001001029900 （v2.4.3 已推送，2026-07-29 17:25）
```

## 工作流

### Step 1 — 加载状态

读取 `{project_root}/.claude/workflow/{需求名}/tapd-wiki.json`（不存在 → 视为首次推送）。

### Step 2 — 读取 current.md

从 `current.md` 提取：
- 需求名（`# 需求：{名称}` 行）
- 主项目路径（`- 主项目：{path}` 行）

### Step 3 — 匹配配置

按主项目路径查 `~/.claude/.tapd-wiki-config.json`：
- 匹配 → 取 `workspace_id`、`parent_wiki_id`、`creator`
- 未匹配 → 终止，输出：

```
⚠ 未找到项目 {主项目路径} 的 TAPD Wiki 配置。
请在 ~/.claude/.tapd-wiki-config.json 的 wiki_targets 中补充：
{
  "name": "{项目名}",
  "project_root": "{主项目路径}",
  "workspace_id": "...",
  "parent_wiki_id": "..."
}
```

### Step 4 — 读取源文件

读取 `{project_root}/workflow/{需求名}/03-技术方案.md`。
文件不存在 → 终止并报错。

### Step 5 — 版本与变更检测

- `new_version` 由调用方传入（如 `v2.4.3`），从 `03-技术方案.md` 顶部版本行或附录 C 取
- 获取源文件 mtime；若 `state.source_md_mtime == 当前 mtime` 且 `state.wiki_id` 存在 → 输出「内容未变更，跳过推送」并结束
- 用户明确要求「重新推送」时跳过 mtime 检测

### Step 6 — 推送（走脚本）

执行：

```bash
# 更新已有 wiki
python3 ~/.claude/skills/tapd-wiki-publish/scripts/push_wiki.py \
    --source "{project_root}/workflow/{需求名}/03-技术方案.md" \
    --workspace-id {workspace_id} \
    --wiki-id {state.wiki_id} \
    --creator {creator} \
    --version {new_version} \
    --name "{需求名} - 技术方案" \
    --state-file "{project_root}/.claude/workflow/{需求名}/tapd-wiki.json" \
    --current-md "{project_root}/.claude/workflow/{需求名}/current.md"
```

首次创建（无 `state.wiki_id`）：

```bash
python3 ~/.claude/skills/tapd-wiki-publish/scripts/push_wiki.py \
    --source "{project_root}/workflow/{需求名}/03-技术方案.md" \
    --workspace-id {workspace_id} \
    --parent-wiki-id {parent_wiki_id} \
    --creator {creator} \
    --version {new_version} \
    --name "{需求名} - 技术方案" \
    --state-file "{project_root}/.claude/workflow/{需求名}/tapd-wiki.json" \
    --current-md "{project_root}/.claude/workflow/{需求名}/current.md"
```

脚本自动：
- 在源 Markdown 顶部插 `> 版本: {version} | 推送时间: {now} | 作者: {creator}` 行（除非 `--no-version-header`）
- POST `https://api.tapd.cn/tapd_wikis?s=mcp`（Bearer + `Via: mcp` 头）
- 写状态文件 `tapd-wiki.json`
- 改 `current.md` 的 `- TAPD Wiki:` 行
- 退出码 0 成功；1 推送失败；2 参数/配置错误

**调试用 `--dry-run`**：只校验参数/token/文件/payload，不发起 HTTP，不写状态文件。

### Step 7 — 推送结果

脚本成功 → 输出：

```
✅ TAPD Wiki 推送成功
- Wiki: {wiki_url}
- 版本: {new_version}
- 父模块: {parent_wiki_id}
- 操作: {创建 | 更新}
- 内容大小: {N} 字符
- 状态文件: {state_file 路径}
- current.md TAPD Wiki 行已更新
```

脚本失败 → 输出错误信息（HTTP 状态码 + 响应体前 2000 字符），**不更新状态文件，不改 current.md**。用户修复后重跑即可。

## 重新推送（评审反馈后）

用户说「重新推送方案」「方案改了再推一次」时：
- 重新执行 Step 4~6
- `state.wiki_id` 已存在 → 走更新分支（`--wiki-id`）
- `new_version` 递增（如 v2.4.3 → v2.4.4），从 `03-技术方案.md` 附录 C 新增版本记录行取
- mtime 检测自动通过（源文件已改）

## 不再使用 mcp 工具的场景

以下场景**禁用 `mcp__tapd__create_wiki` / `update_wiki`**：
- 任何 Markdown 文件 ≥ 30KB
- 任何 `03-技术方案.md` / `04-开发编码.md` 等结构化产物（无论大小，统一走脚本）

以下场景可继续用 mcp 工具：
- 查询单个 wiki 内容（`mcp__tapd__get_wiki`）— 无大参数
- 推送短篇 wiki（< 30KB，如一段变更说明）

## 注意事项

- **不修改源文件**：`03-技术方案.md` 保持纯净，版本行只在推送时由脚本插
- **mtime 检测**：避免无意义的重复推送
- **creator 字段**：从配置文件全局 `creator` 读取，不每次询问
- **Wiki URL 格式**：`https://www.tapd.cn/{workspace_id}/markdown_wikis/show/#{wiki_id}`
- **token 权限**：`~/.claude/.tapd-wiki-config.json` 应保持 600 权限，避免泄露
