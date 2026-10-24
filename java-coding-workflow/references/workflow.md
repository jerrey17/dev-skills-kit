# Workflow

## 目标

已有仓库 TDD 编码的完整单会话闭环，支持多服务编排。包含服务拆分文档解析、共享 KB 扫描、git worktree 创建、TDD 循环、commit & push、需求级汇总报告等环节。

---

## 总览

```
Phase 0: 环境准备
  0a — 仓库就绪检查
  0b — 服务拆分文档解析 & 服务列表构建
  0c — 知识库预扫描（全局唯一，多服务共享）
  0d — 需求分析上下文加载
  0e — 为每个服务创建 Worktree
  0f — GitNexus 业务知识查询

Phase 1: 按服务顺序执行编码（核心编排）
  for each service:
    1.1 — 任务识别
    1.2 — 复用检索 & 组件参考包物化（含共享缓存）
    1.3 — 技术方案解析 & 业务完整性回溯
    1.4 — TDD 编码循环
    1.5 — 依赖版本对齐
    1.6 — 编译验证
    1.7 — 集成测试（可选）
    1.8 — Git Commit & Push（本服务）

Phase 2: 汇总审计与报告
Phase 3: 中间产物清理
```

---

## Phase 0：环境准备

### 0a — 仓库就绪检查

对所有涉及服务的仓库逐一执行：

```bash
git -C {repo_path} rev-parse --show-toplevel   # 确认 git 仓库
git -C {repo_path} status --porcelain           # 确认工作区干净
git -C {repo_path} branch --show-current        # 记录基础分支
```

检查每个仓库存在 `build.gradle` / `pom.xml` / `settings.gradle`。若有未提交变更，提示用户处理后继续。

### 0b — 服务拆分文档解析 & 服务列表构建

1. 检查 `workflow/{需求名}/02-服务拆分.md` 是否存在
2. 存在 → 解析"五、服务改动总览"，提取所有角色为`主责`或`协同`的服务
3. 不存在 → `service_count=1`，单服务模式，使用 `--repo-root` 作为唯一服务路径

产出 `.coding-service-plan.json`：

```json
{
  "requirement": "需求标题",
  "feature_branch_prefix": "feature/xxx",
  "services": [
    {
      "name": "ins-user",
      "role": "主责",
      "local_repo_path": "/path/to/ins-user",
      "spec_doc": "workflow/xxx/03-技术方案-ins-user.md",
      "spec_section": null,
      "worktree_path": null,
      "branch_name": "feature/xxx-ins-user",
      "status": "pending"
    }
  ],
  "shared_kb_dir": "{workflow_dir}/.coding-shared-kb/",
  "shared_component_cache_dir": "~/.claude/coding-component-references-cache/"
}
```

技术方案文档定位规则（按优先级）：
- `workflow/{需求名}/03-技术方案-{服务名}.md`（最优先）
- `workflow/{需求名}/03-技术方案.md` 中 `## {服务名}` 章节
- `workflow/{需求名}/03-技术方案.md` 全文（兜底）
- 均无 → 暂停，提示用户补充

向用户展示服务列表和技术方案对应关系，等待确认后继续。

### 0c — 知识库预扫描（全局唯一）

KB 只扫一次，产出写入 `{workflow_dir}/.coding-shared-kb/`：

```bash
python3 {skill_scripts_dir}/scan_kb_and_materialize.py \
  --output-dir {workflow_dir}/.coding-shared-kb/

python3 {skill_scripts_dir}/build_rule_bundle.py \
  --output-dir {workflow_dir}/.coding-shared-kb/
```

产出：
- `.coding-kb-index.json`
- `.coding-rules.json`（必须含 `detection_profile` 和标准目录结构分类）
- `.coding-dependency-versions.json`

**复用规则**：若 `.coding-rules.json` 存在且 `generated_at` 在 24h 内，跳过扫描，直接使用缓存。

MCP 不可用时立即终止，不允许降级。

### 0d — 需求分析上下文加载

检查 `workflow/{需求名}/01-需求分析.md` 是否存在：
- 存在 → 提取写入 `{shared_kb_dir}/.coding-req-summary.json`

输出知识就绪状态表：

```
知识就绪状态：
✅ 知识库规则：{N} 条
✅ 公共组件版本：{N} 项
✅ 需求分析摘要：已加载
ℹ️  服务拆分：{N} 个服务（或 单服务模式）
```

### 0e — 为每个服务创建 Worktree

遍历 `.coding-service-plan.json` 中的服务列表，为每个服务独立创建：

```bash
# 分支名：{feature_branch_prefix}-{服务名}
# 示例：feature/sms-login-ins-user

git -C {local_repo_path} worktree add \
  {local_repo_path}/../{repo_name}-{branch_name} \
  -b {branch_name}
```

创建后更新 `.coding-service-plan.json` 中对应服务的 `worktree_path` 和 `status=worktree_ready`。

### 0f — GitNexus 业务知识查询

针对主责服务查询，写入 `{worktree_path}/.coding-gitnexus-cache.json`：

```
mcp__gitnexus__query(核心调用链)
mcp__gitnexus__context(已有接口签名)
```

不可用时记录 `unavailable`，不阻断流程。

---

## Phase 1：按服务顺序执行编码

服务按 `主责 → 协同` 顺序串行执行。某服务 `blocked` 时暂停，等待用户确认是否跳过或修复后继续。

### 1.1 — 任务识别

在服务的 worktree 目录内执行：

```bash
python3 {skill_scripts_dir}/detect_targets.py \
  --shared-kb-dir {shared_kb_dir} \
  --spec {service.spec_doc} \
  --spec-section {service.spec_section} \
  --module-root {worktree_path}
```

产出：`.coding-targets.json`、`.coding-spec-summary.json`、`.coding-bootstrap.json`（均写入 worktree 目录）

### 1.2 — 复用检索 & 组件参考包物化

```bash
python3 {skill_scripts_dir}/build_reuse_bundle.py \
  --shared-kb-dir {shared_kb_dir} \
  --workdir {worktree_path}
```

**组件参考包缓存规则**：

- 缓存目录：`~/.claude/coding-component-references-cache/{artifact_id}-{version}/`
- 缓存命中 → 直接 symlink 到 `{worktree_path}/.coding-component-references/`，跳过 MCP 物化
- 缓存未命中 → 走完整物化流程，完成后写入缓存目录
- 缓存 TTL：24h，与 KB 扫描一致

`must_reuse` 组件 `doc_status != loaded` → 阻断。

### 1.3 — 技术方案解析 & 业务完整性回溯

**解析**：

```bash
python3 {skill_scripts_dir}/parse_spec.py \
  --spec {service.spec_doc} \
  --spec-section {service.spec_section}
```

仅解析当前服务对应的技术方案章节，不跨服务解析。

**完整性回溯**：

对照三个 JSON 快照，检查差异，写入 `.coding-spec-review.json`。发现缺失项时暂停等待用户确认。

### 1.4 — TDD 编码循环

详细步骤参见 [tdd-guide.md](tdd-guide.md)。

**4a — 生成文件计划**

```bash
python3 {skill_scripts_dir}/generate_code_skeleton.py
```

前置校验：必须有 `unit-test` 条目。

**4b — 测试骨架生成（先于业务代码）**

1. 读取所有 `kind=unit-test` 条目
2. 生成带 `@Disabled` 空方法体的测试类，落盘到 `src/test/java/`
3. 向用户展示场景列表，等待确认

**多服务批量确认优化**：若多服务并行，在第一个服务的 4b 时同时展示所有服务的测试骨架，用户统一确认后各服务开始业务代码实现。

**4c — 业务代码实现**

按 `.coding-brief.json` + `.coding-file-plan.json` 落地业务代码，严格遵循 SKILL.md 中所有规范原则。

**4d — 测试用例补全**

填充所有 `@Disabled` 方法体（Given-When-Then），移除 `@Disabled`。

**4e — TDD 循环执行**

```
round = 1
while round <= 3:
    执行 run_unit_tests.py
    若 passed → 退出循环
    若 failed:
        分析失败原因（业务代码问题优先）
        修改 src/main/java/ 下业务代码
        记录到 .coding-test-repair.json round {N}
        round += 1

若 round > 3 且仍有失败 → status = blocked，输出剩余失败集
```

### 1.5 — 依赖版本对齐

```bash
python3 {skill_scripts_dir}/align_dependency_versions.py \
  --shared-kb-dir {shared_kb_dir} \
  --path {worktree_path}
```

产出：`.coding-version-alignment.json`

### 1.6 — 编译验证

```bash
python3 {skill_scripts_dir}/run_compile_check.py
```

最多 3 轮修复，失败则 `blocked` 终止。产出：`.coding-compile-check.json`

### 1.7 — 集成测试（可选）

触发条件参见 [tdd-guide.md](tdd-guide.md)。执行失败记录到报告，不阻断主流程，不进入自动修复。

### 1.8 — Git Commit & Push（本服务）

详细步骤参见 [worktree-guide.md](worktree-guide.md)。

```bash
git -C {worktree_path} add {specific_files}
git -C {worktree_path} commit -m "feat(ins-user): 实现短信验证码登录\n\n按技术方案完成..."
git -C {worktree_path} push -u origin {branch_name}
```

推送成功后输出该服务的 PR 提示，更新 `.coding-service-plan.json` 中本服务 `status=completed`。

---

## Phase 2：汇总审计与报告

所有服务编码完成后（或部分 `blocked` 经用户确认跳过后）：

```bash
python3 {skill_scripts_dir}/summarize_report.py \
  --service-plan {workflow_dir}/.coding-service-plan.json \
  --output {workflow_dir}/coding-assistant-report-YYYY-MM-DD-HHMM.md
```

报告包含：
- 各服务编码结果汇总表（服务名、状态、分支、PR 链接、TDD 结论）
- 每个服务规范检查详情（折叠展示）
- 跨服务共享组件复用情况
- 跨服务规范缺口汇总

---

## Phase 3：中间产物清理

报告成功输出后：

1. 清理各 worktree 目录下的 `.coding-*.json`
2. 清理 `{shared_kb_dir}/`（保留 24h 内有效的 KB 缓存，供本需求其他服务续跑复用）
3. **保留** `~/.claude/coding-component-references-cache/`（长期缓存，跨需求复用）
4. 保留最终 Markdown 报告和代码改动
5. 任一步骤失败时保留对应服务的现场，不清理

---

## 常用断点与续跑

### 暂停在测试骨架确认后

```bash
python3 scripts/run_existing_repo_workflow.py \
  --workflow-dir /path/to/workflow/需求名称/ \
  --pause-after-test-skeleton
```

### 从 TDD 循环阶段续跑（指定服务）

```bash
python3 scripts/run_existing_repo_workflow.py \
  --workflow-dir /path/to/workflow/需求名称/ \
  --service ins-user \
  --resume-from tdd-loop
```

### 跳过 KB 扫描（有效期内）

```bash
python3 scripts/run_existing_repo_workflow.py \
  --workflow-dir /path/to/workflow/需求名称/ \
  --skip-kb-scan
```

前提：`{shared_kb_dir}/.coding-rules.json` 存在且 `generated_at` 在 24h 内。

### 按阶段续跑可选值

`kb-scan` → `worktree` → `detect` → `reuse` → `reference-pack` → `brief` → `file-plan` →
`test-skeleton` → `implement` → `test-completion` → `tdd-loop` →
`compile` → `integration-test` → `commit` → `audit` → `report` → `cleanup`

### 仅重跑某个服务

```bash
python3 scripts/run_existing_repo_workflow.py \
  --service-plan /path/to/.coding-service-plan.json \
  --only-service ins-user
```

---

## 中间产物分布汇总

**需求级（`{workflow_dir}/`）**

```
.coding-service-plan.json
.coding-shared-kb/
  ├── .coding-kb-index.json
  ├── .coding-rules.json
  ├── .coding-dependency-versions.json
  └── .coding-req-summary.json
coding-assistant-report-*.md   ← 保留
```

**服务级（各 `{worktree_path}/`）**

```
.coding-bootstrap.json
.coding-gitnexus-cache.json
.coding-spec-review.json
.coding-targets.json
.coding-spec-summary.json
.coding-reuse.json
.coding-component-references/  ← 软链自长期缓存
.coding-brief.json
.coding-file-plan.json
.coding-version-alignment.json
.coding-compile-check.json
.coding-test-run.json
.coding-test-repair.json
.coding-audit.json
```

**长期缓存（`~/.claude/coding-component-references-cache/`）**

```
{artifact_id}-{version}/       ← 跨需求保留，不清理
```
