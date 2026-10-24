---
name: workflow-learnings-to-kb
description: >
  把 dev-workflow 的 decisions.md 和 10-复盘.md 中可复用的经验沉淀到本地知识库。
  TRIGGER: 用户说"沉淀经验到知识库"、"把这次经验写入 KB"、"复盘后沉淀"、"workflow-learnings-to-kb"、"/workflow-learnings-to-kb"；
  或 dev-workflow 复盘阶段完成后由用户主动调用。
  不做 hook 自动化，必经人工审核 gate 后才写入 KB。
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
---

# workflow-learnings-to-kb — 工作流经验沉淀

## 定位

dev-workflow 末端的独立 skill,把单次需求开发过程中产生的可复用经验沉淀回本地知识库。纯按需触发,不做 hook、不做自动写入、不做跨需求合并。

## 输入

- **工作流目录**: `{项目根目录}/.claude/workflow/{需求名称}/`
  - 用户显式指定 → 优先使用
  - 未指定 → 扫描 `{当前工作目录}/.claude/workflow/*/` 和 `~/.claude/workflow/*/`,按最后修改时间倒序列出供用户选择
- **KB 根路径**: 从 `~/.claude/skills/tech-solution-design/scripts/kb.config.json` 读 `kb_root`,与 tech-solution-design 等其他 skill 共用配置

## 候选来源(仅以下两类)

| 来源文件 | 提取什么 |
|---------|---------|
| `.claude/workflow/{需求}/decisions.md` | 决策记录、被否定方案、约束条件 |
| `workflow/{需求}/10-复盘.md` | 问题根因、防止再犯清单、踩坑案例 |

**不纳入 `04-开发编码.md`** — 开发实现细节多含一次性代码,通用性抽取成本高。作为后续优化项,先验证 decisions + 复盘的效果。

## 执行流程

### Step 1 — 确定工作流目录与 KB 根

1. 确定工作流目录(见"输入"节)。若扫描到多个,列表让用户选;若一个都没有,终止并提示用户先跑 dev-workflow。
2. 读 `~/.claude/skills/tech-solution-design/scripts/kb.config.json` 获取 `kb_root`。配置缺失或 `kb_root` 不存在时,终止并提示用户先配置。
3. 读 `{kb_root}/_INDEX.md` 建立 KB 全局视图(域 → 模块 → 文件)。

### Step 2 — 扫描工作流产物

读取以下文件(有则读,缺失则跳过并在最后汇总时标注):

- `{工作流目录}/decisions.md`
- `{项目根目录}/workflow/{需求名称}/10-复盘.md`(注意:`10-复盘.md` 在正式产物目录,不在 `.claude` 下)

若两个文件都不存在,终止并提示用户:该需求尚未产出可沉淀的经验。

### Step 3 — LLM 抽取候选经验

对 decisions.md 和 10-复盘.md 中的每条决策/问题/根因,执行以下分析:

**通用性判定**(关键 gate):
- **一次性问题**(如"本次因为某上游接口字段缺失临时加了 null 处理")→ 跳过,不沉淀
- **可能复现的经验**(如"跨境汇款订单 ID 命名约定"、"PB 响应错误码必须用 ResponseBasic.scode 而非自定义字段")→ 保留

通过通用性判定的候选,标注:

| 字段 | 说明 |
|------|------|
| 标题 | 一句话概括经验 |
| 类别 | 规范补丁 / 反模式 / 命名约定 / 公共组件接入要点 / 踩坑案例 / 工具使用技巧 |
| 来源 | decisions.md 或 10-复盘.md 的具体条目(含日期、决策主题) |
| 域归属 | 对照 KB `_INDEX.md` 的域分类(base_specifications / contract / sms / 规范类 / 工具类)。无法判断标"未分类"让用户选 |
| 目标位置 | 已有文件(追加段落)或新建文件(需注册索引) |
| 内容草案 | 准备写入的 Markdown 段落 |

### Step 4 — 去重比对

对每条候选,在 KB 中做语义去重:

1. 从候选标题和内容提取 3-5 个关键词
2. 调用 `call_kb.py search` 检索 KB:
   ```bash
   python3 ~/.claude/skills/tech-solution-design/scripts/call_kb.py search -k "<关键词>"
   ```
3. 对返回的命中文件,读对应段落,判断是否语义重叠:
   - **完全重叠**:标"已收录",跳过(不写入 proposal)
   - **部分重叠**:标"已收录,可补充新角度",在内容草案中只写与现有内容**不同**的部分
   - **无重叠**:标"新增"

### Step 5 — 生成变更草案

输出到 `{工作流目录}/.kb-sync-proposal.md`,格式:

```markdown
# KB 沉淀草案 — {需求名称}

> 生成时间: {YYYY-MM-DD HH:MM}
> 来源: decisions.md + 10-复盘.md
> 候选总数: {N} 条(新增 {X} / 补充 {Y} / 已收录跳过 {Z})

## 候选 1: {标题}
- 类别: {类别}
- 来源: {decisions.md 2026-07-15 决策"XXX"}
- 域归属: {contract / 规范类 / 未分类}
- 目标: {kb_root}/{相对路径}.md(已有文件,追加 ## {段落标题} 一节)
- 操作: {追加段落 / 新建文件}
- 去重: {新增 / 已收录可补充新角度: {简述重叠位置}}
- 内容草案:
  ```markdown
  {准备写入的段落}
  ```

## 候选 2: ...

## 已跳过(一次性或已收录)
- {条目标题}: {跳过原因}
```

### Step 6 — 人工审核(必经 gate)

逐条向用户展示候选,每条选项:

- **accept** — 按草案写入
- **edit** — 用户改内容/目标位置/域归属后再 accept
- **reject** — 不写入

支持批量操作:用户可对某类别的候选全选 accept,或对"已收录可补充新角度"类全选 accept。

### Step 7 — 写入 KB

对 accepted 条目执行:

1. **追加段落到已有文件**:用 Edit 工具在目标文件末尾或对应章节后追加
2. **新建文件**:
   - 在 `{kb_root}/{域}/{模块}/` 下创建新 `.md` 文件
   - 同步更新该域的 `_INDEX.md`(若域有模块级索引)和根 `_INDEX.md` 的域条目表
   - 索引表格行格式参照现有条目:`| [文件名](相对路径) | 行数 | 关键词 | 说明 |`
3. **不碰 git**:本地 KB 是目录,不 commit、不 push、不建分支

### Step 8 — 输出汇总

```
✅ 沉淀完成: {需求名称}

- 写入: {N} 条
  · 新增文件: {列出文件路径}
  · 追加段落: {列出目标文件 + 段落标题}
  · 索引更新: {列出更新的 _INDEX.md 路径}
- 跳过: {M} 条
  · 一次性问题: {K} 条
  · 已收录: {L} 条
- 草案保留: {工作流目录}/.kb-sync-proposal.md

下一步: 审核沉淀效果,后续迭代可纳入 04-开发编码.md 等更多来源。
```

## KB 写入约束

- **不动 git**:本地 KB 暂时仅本地维护,未来若 KB 改为 git 仓库再另行加 commit 步骤
- **域分类强制**:新建文件必须落到某个域目录下,或经用户确认归到"规范类"等跨域目录。不允许散落在 KB 根目录
- **索引同步强制**:新建文件而不更新 `_INDEX.md` 视为未完成,会在 Step 7 报错提示
- **不覆盖已有内容**:追加段落时若目标位置已有同标题章节,改"追加"为"在现有章节后补内容",避免覆盖

## 与其他 skill 的关系

- **dev-workflow**:本 skill 不依赖 dev-workflow 主动调用,由用户在复盘后或任意时机独立触发。dev-workflow 的"阶段完成"提示可选追加"建议沉淀经验"指引,但不强制
- **tech-solution-design**:共用 `~/.claude/skills/tech-solution-design/scripts/call_kb.py` 做 KB 读取/搜索,不重复造轮子
- **java-techdesign-coding-closure**:未来可扩展读取 `compliance-report.md` / `governance-report.md` 作为额外候选来源,本期不纳入
- **sync-knowledge-docs**:方向相反(KB → 项目),不复用

## 人工 gate 边界

以下场景**必须**等用户明确确认后才能执行:

1. 写入 KB 前的 accept/reject/edit(Step 6)
2. 域归属"未分类"时让用户指定域
3. 新建文件时让用户确认文件名和域位置
4. 索引行内容(文件名/关键词/说明)写入前向用户展示

**不允许**跳过 gate 直接写。

## 终止条件

出现以下任一情况终止:

1. 工作流目录不存在或无法识别
2. `kb.config.json` 缺失或 `kb_root` 不存在
3. `decisions.md` 和 `10-复盘.md` 均不存在
4. `_INDEX.md` 不可读(KB 结构无法建立)

## 未来扩展(本期不做)

- 纳入 `04-开发编码.md` 关键实现说明作为第三类候选来源(需先验证 decisions + 复盘的沉淀效果)
- 纳入 `java-techdesign-coding-closure` 的 `compliance-report.md` 规范问题与修正
- 跨需求候选队列(若单需求候选不足 1 条,积累到队列批量沉淀)
- KB git 化后的自动 commit + PR 流程
