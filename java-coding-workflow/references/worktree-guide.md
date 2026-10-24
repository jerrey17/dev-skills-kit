# Git Worktree 操作指南

## 为什么用 Worktree？

- 保持主干干净，需求开发在独立目录进行
- 无需切换分支，可同时查看主干和特性分支代码
- 推送后直接创建 PR，流程清晰

---

## Phase 0b 详细操作步骤

### Step 1 — 确认仓库根目录

```bash
# 确认 git 仓库根目录
git -C {repo_root} rev-parse --show-toplevel

# 确认工作区干净（无未提交变更）
git -C {repo_root} status --porcelain
```

若有未提交变更，输出：
```
⚠ 当前工作区有未提交变更，请先处理：
  - 暂存：git stash
  - 提交：git commit
  - 放弃：git checkout .
```

### Step 2 — 推导分支名

分支名规则：

| 场景 | 前缀 | 示例 |
|------|------|------|
| 新功能开发 | `feature/` | `feature/sms-login` |
| Bug 修复 | `fix/` | `fix/payment-timeout` |
| 代码重构 | `refactor/` | `refactor/user-service` |
| 配置/脚手架 | `chore/` | `chore/upgrade-gradle` |

推导来源优先级：
1. 用户显式提供 `--branch-name`
2. 从技术方案标题提取，转小写 + 连字符
3. 从需求分析 `01-需求分析.md` 标题提取

### Step 3 — 检查分支冲突

```bash
# 检查本地和远端是否已存在同名分支
git -C {repo_root} branch -a | grep {branch_name}
```

若已存在：
```
⚠ 分支 {branch_name} 已存在，请选择：
  1. 使用已有分支创建 worktree（git worktree add ... {branch_name}）
  2. 修改分支名（如加后缀 -v2）
```

### Step 4 — 创建 Worktree

```bash
# 标准命令（在仓库同级目录创建 worktree）
REPO_NAME=$(basename {repo_root})
WORKTREE_PATH="{repo_root}/../${REPO_NAME}-{branch_name}"

git -C {repo_root} worktree add "$WORKTREE_PATH" -b {branch_name}
```

成功后输出：
```
✅ Worktree 已创建
   路径：{worktree_path}
   分支：{branch_name}
   
后续所有编码操作将在此路径进行。
```

### Step 5 — 验证 Worktree

```bash
git -C {repo_root} worktree list
```

---

## Phase 8 详细操作步骤

### Step 8a — Stage 文件

精确 stage，避免提交敏感文件：

```bash
# 查看变更列表
git -C {worktree_path} diff --stat

# 精确 add（不使用 git add .）
git -C {worktree_path} add src/main/java/...
git -C {worktree_path} add src/test/java/...

# 确认暂存内容
git -C {worktree_path} diff --cached --stat
```

**禁止 stage 的文件类型**：

- `.env`、`.env.*`
- 包含密码、token、密钥的配置文件
- IDE 配置文件（`.idea/`、`.vscode/`）
- 中间产物 `.coding-*.json`
- 构建产物（`build/`、`target/`）

### Step 8b — 生成 Commit Message

格式（Conventional Commits）：

```
{type}({scope}): {功能简述，英文，不超过 50 字符}

{改动原因和背景，中文，可多行}

{可选：关联 issue 或 TAPD ID}
```

示例：

```
feat(user-login): 新增短信验证码登录功能

实现用户手机号+短信验证码的登录流程，替换原有密码登录入口。
验证码有效期 5 分钟，同一手机号 60 秒内不允许重复发送。

TAPD: #12345678
```

### Step 8c — 执行 Commit

```bash
git -C {worktree_path} commit -m "$(cat <<'EOF'
{commit_message}
EOF
)"
```

### Step 8d — Push

```bash
git -C {worktree_path} push -u origin {branch_name}
```

推送成功后输出 PR 提示：

```
✅ 代码已推送到远端分支：{branch_name}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
下一步：创建 Pull Request
  目标分支：{base_branch}（如 main / develop）
  源分支  ：{branch_name}
  
使用 GitHub CLI：
  gh pr create \
    --base {base_branch} \
    --head {branch_name} \
    --title "{commit_message_title}" \
    --body "## 变更说明
{commit_message_body}"
    
或访问仓库页面手动创建 PR。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Worktree 生命周期管理

### 查看所有 Worktree

```bash
git worktree list
```

### 开发完成后清理 Worktree（PR 合并后）

```bash
# 删除 worktree（不删除分支）
git worktree remove {worktree_path}

# 若有未提交变更，加 --force 强制删除（谨慎）
git worktree remove --force {worktree_path}

# PR 合并后，删除本地分支
git branch -d {branch_name}
```

### 恢复被意外删除的 Worktree 记录

```bash
git worktree prune
```

---

## 常见问题

### Q: Worktree 创建失败，提示"已存在"

```bash
# 查看 worktree 状态
git worktree list

# 清理已删除目录的 worktree 记录
git worktree prune
```

### Q: Push 失败，提示"远端已有同名分支"

若远端已有同名分支且有不同提交，需要先确认：

```bash
# 查看远端分支状态
git fetch origin {branch_name}
git log --oneline origin/{branch_name}..HEAD

# 若本地领先，正常推送
# 若有分叉，rebase 后推送（不强推）
git rebase origin/{branch_name}
git push -u origin {branch_name}
```

### Q: 如何从 Worktree 切回主干继续其他工作

Worktree 是独立目录，直接切换终端目录到主仓库即可，无需任何 git 命令。
