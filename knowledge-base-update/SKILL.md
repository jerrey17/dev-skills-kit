---
name: knowledge-base-update
description: 知识库更新 skill（dev-workflow 自动节点）。复盘完成后由 dev-workflow 自动触发，无需人工确认：本次改动服务逐仓切回 master、拉取最新代码、重建 GitNexus 索引，产出 workflow/{需求名称}/11-知识库更新.md。也可独立调用（"更新知识库索引"、"重建 gitnexus 索引"、"切回 master"）。
---

# knowledge-base-update — 知识库更新

## 定位

dev-workflow 末端**自动节点**。复盘阶段完成（`10-复盘.md` 已产出并经用户审核）后由 dev-workflow 自动调用，不展示阶段审核提示、不等待人工确认。

与 `workflow-learnings-to-kb` 的区别：后者是**经验沉淀**（决策/复盘经验写入知识库，人工审核 gate，按需调用）；本 skill 是**环境复位 + 代码索引刷新**（自动）。两者可在复盘后先后执行，互不替代。

设计依据：GitNexus 索引只在发布生产后重建，开发中途提示过期不执行 analyze。本节点把这条规则固化为流程动作。

## 输入

- `.claude/workflow/{需求名称}/current.md`：主项目 + 关联项目（本次有代码改动的仓库）
- 标注为"协同只读 / 零改动"的仓库**不处理**（无需切分支、无需重建索引）

## 执行步骤

### Step 1 — 确定仓库清单

读 `current.md` 的"主项目"和"关联项目"，筛出本次有代码改动的仓库，去重。

### Step 2 — 逐仓 pre-check（安全闸门）

对每个仓库依次检查：

1. **工作区干净（仅看已跟踪文件）**：`git -C {repo} status --porcelain -uno` 非空 → **跳过该仓**，记录原因"有未提交改动"。注意必须加 `-uno`：未跟踪文件（`.claude/`、`config-cache/` 等）不阻塞切分支，不视为脏工作区
2. **无未推送 commit**：先 `git -C {repo} rev-parse --abbrev-ref @{u}` 探测 upstream——
   - 有 upstream：`git -C {repo} log @{u}..HEAD --oneline` 非空 → **跳过该仓**，记录原因"有未推送 commit"
   - 无 upstream 但 origin 存在同名分支：用 `git -C {repo} log origin/{分支}..HEAD --oneline` 代替判断
   - 无 upstream 且 origin 无同名分支：不阻塞（提交只存在于本地分支，切 master 不会丢失），记录"当前分支未跟踪远端，跳过未推送检查"
3. **检测默认分支**：`git -C {repo} symbolic-ref refs/remotes/origin/HEAD` 取默认分支；失败则依次探测 `master` / `main`

**铁律**：任何 pre-check 不通过 → 跳过该仓并记录原因，继续处理其他仓。全程禁止 `reset` / `clean` / `checkout -f` / `stash` / `branch -D` 等破坏性命令。跳过项在执行完毕后统一告知用户，由用户决定手工处理。

### Step 3 — 切回默认分支 + 拉取最新代码

对每个通过 pre-check 的仓库：

```bash
git -C {repo} checkout {默认分支}     # 已在默认分支则跳过
git -C {repo} pull --ff-only          # 非 fast-forward 则记录失败，不 rebase 不 merge
```

pull 后顺带报告：该仓 master 是否已包含本次需求的分支改动（`git -C {repo} branch --merged | grep {feature分支}`），未包含则在记录中标注"master 尚未合并本次改动（发布平台合并可能有延迟）"——不阻断，索引反映的是 master 当前状态。

### Step 4 — 重建 GitNexus 索引

仅对**已被 GitNexus 索引**的仓库执行：

```bash
cd {repo} && npx gitnexus analyze
```

判断已索引：`~/.gitnexus/` 下存在该仓的索引数据，或 `npx gitnexus status` 显示已索引。未索引的仓跳过并记录"未被 GitNexus 索引，跳过 reindex"。

### Step 5 — 写执行记录并置终态

写入 `workflow/{需求名称}/11-知识库更新.md`：

```markdown
# 11-知识库更新 — {需求标题}

- 执行时间：{日期时间}
- 触发方式：复盘完成后自动执行

## 执行结果

| 仓库 | pre-check | checkout master | pull --ff-only | gitnexus analyze | 备注 |
|------|-----------|----------------|----------------|------------------|------|
| demo-service | ✅ | ✅ | ✅（+12 commits） | ✅ | master 已含本次改动 |
| demo-web | ⏭ 跳过：有未提交改动 | — | — | — | 待用户手工处理 |

## 跳过项与后续建议

{跳过仓清单 + 原因 + 建议处理方式}

## 小结

- 产出: workflow/{需求名称}/11-知识库更新.md
- 阻塞: {无，或跳过仓清单}
- 已知缺口: {无，或未重建索引的仓}
- 交接: 流程结束；跳过项由用户决定是否手工处理
```

更新 `current.md`：
- 勾选 `11-知识库更新.md`
- 当前阶段 = `流程结束`
- 上次操作 = "知识库更新完成：N 仓已复位+索引重建，M 仓跳过"
- 待办 = 跳过项处理建议（无则"无"）

### Step 6 — 汇总输出

执行完毕后向用户输出汇总（这是自动节点唯一的人工触点）：

```
✅ 知识库更新（自动节点）执行完毕：
· 已复位 + 索引重建：{仓清单}
· 跳过：{仓 + 原因}
· 跳过项处理建议：{如"atm.win 有未提交改动，请确认后手工 git checkout master && git pull && npx gitnexus analyze"}
需求全流程已结束。
```

## 独立调用

用户说"更新知识库索引"、"重建 gitnexus 索引"、"把 XX 仓切回 master 并更新索引"时，可脱离 dev-workflow 独立执行：仓库清单由用户指定（而非读 current.md），其余步骤相同。

## 产出文件

`workflow/{需求名称}/11-知识库更新.md`（独立调用时可选，用户不要求则不写）
