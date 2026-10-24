---
name: java-coding-workflow
description: Java 后端编码助手，骨架优先 + 逐功能 TDD。统一入口，内部自行判断是否需要 scaffold。当 dev-workflow 进入开发编码阶段时调用，也可独立使用。
---

# java-coding-workflow — 骨架优先 + 逐功能 TDD 的 Java 编码助手

## 定位与哲学

本 skill 是开发编码的**唯一入口**。内部自行判断是否需要 scaffold、是否需要 worktree，调用方无需分流。

核心哲学：
1. **先骨架后血肉** — Phase 1 创建完整文件骨架、连通集成点、编译通过，Phase 2 逐功能 TDD 补全
2. **功能点粒度追踪** — 状态表按功能点拆分（✅/🔶/❌），不按服务聚合
3. **已知缺口显式化** — 小结必须列出"标记完成但实现不完整"的项

## 流程总览

```
Phase 0: 环境与知识准备
  ├── 仓库就绪检查（缺失 → java-project-scaffold）
  ├── 服务拆分文档解析
  ├── 知识库预扫描
  ├── Worktree 创建
  └── GitNexus 查询

Phase 1: Walking Skeleton
  ├── 创建所有文件的骨架（Controller/Service/DTO/Config/Client）
  ├── 依赖注入 + Apollo 配置 + 模块间依赖
  ├── 编译验证
  └── 产出功能点状态表

Phase 2: TDD Flesh
  └── 逐功能点：写测试 → 补实现 → 绿灯 → 标记 ✅

Phase 3: Code Verification
  ├── 读代码核查每个 ✅（确认非骨架）
  └── 编译 + 全量测试

Phase 4: Summary & Report
  ├── 生成汇总报告（功能点状态表 + 各服务 commit 链接）
  └── 写入 4-bullet 小结
```

## 功能点状态

| 状态 | 含义 | 判定标准 |
|------|------|---------|
| ✅ | 已完成 | Phase 3 代码核查通过（测试绿灯 + 方法体非骨架） |
| ⏳ | 待核查 | Phase 2 TDD 完成、测试绿灯，等待 Phase 3 代码核查 |
| 🔶 | 骨架就绪 | 编译通过，端点可调，核心逻辑待实现 |
| ❌ | 未开始 | 文件未创建或仅创建空类 |
| ↩ | 已延后 | 不在本次交付范围（P2 项或被外部阻塞），记录延期原因 |

**状态流转**：

```
                  Phase 1               Phase 2            Phase 3
                  (Skeleton)            (TDD)              (Verify)

❌ ────────────→ 🔶 ────────────────→ ⏳ ────────────→ ✅
未开始           骨架就绪              待核查            已完成
                 │                     │                 │
                 │                     └──→ 🔶 (回退)     ├──→ 🔶 (回退，补实现)
                 │                     (发现骨架)         │
                 └──→ ✅ (纯校验/枚举)                     └──→ ↩ (延后，P2/外部阻塞)
                       │                                  (不在本次交付)
                       └──→ 🔶 (Phase3 发现缺陷，回退)
```

**回退规则**：
- `⏳ → 🔶`：Phase 3 核查发现方法体仍是骨架 → 回到 Phase 2 补实现
- `✅ → 🔶`：Phase 3 核查发现纯校验逻辑有缺陷 → 回到 Phase 2 修复 + 补测试
- 回退时必须在状态表说明列记录回退原因

**延后规则**：
- P2 功能点或受外部阻塞的项，用户确认后标记 `↩`
- `↩` 项不出现在"已知缺口"中（已明确延后，不是缺口）
- `↩` 项出现在最终报告的"延后项"清单中

**跨会话恢复**：
- 读 `04-开发编码.md`（或独立模式下的编码报告），定位状态表中非 `✅` 且非 `↩` 的项
- 从对应 Phase 继续（🔶 → Phase 2，⏳ → Phase 3）

---

## Phase 0: 环境与知识准备

Phase 0 的所有步骤均适配两种运行模式：
- **dev-workflow 模式**：读取 `02-服务拆分.md` 和 `03-技术方案.md`
- **独立模式**：从当前目录推断仓库路径，技术方案由用户提供或从代码反向推断

### Step 0a — 仓库就绪检查

1. **dev-workflow 模式**：从 `02-服务拆分.md`「五、服务改动总览」读取服务列表
2. **独立模式**：当前目录即为唯一服务仓库，确认 `pom.xml` 或 `build.gradle` 存在
3. 如果仓库不存在本地 → 调用 `java-project-scaffold` 生成项目骨架

### Step 0b — 服务与技术方案定位

**dev-workflow 模式**：
- 服务列表从 `02-服务拆分.md` 解析
- 技术方案文档定位（按优先级）：
  1. `03-技术方案-{服务名}.md`（独立文件，最优先）
  2. `03-技术方案.md` 中匹配 `## {服务名}` 或 `### {服务名}` 章节
  3. **提取当前服务相关内容**（非全文回退）：
     - 先读方案 `§4 涉及的服务/系统` 或 `## 四、服务改动总览`，确认各服务职责边界
     - 从方案中提取当前服务相关的接口定义、DDL、流程章节
     - 其他服务的接口/DDL/流程图**不加载**到当前服务上下文

**独立模式**：
- 单服务模式，服务名 = 当前目录名
- 技术方案来源（按优先级）：
  1. 用户指定的 Markdown 文件路径
  2. 用户口述的功能描述（记录为简要方案）
  3. 从 GitNexus query 推断功能上下文

### Step 0c — 知识检索（GitNexus 优先，知识库补充规范）

**检索顺序**：

1. **GitNexus Group 定位代码上下文**：
   - 调用 `mcp__gitnexus__group_list` 查询当前仓库所属 group
   - 通过 group 锁定关联服务的调用链和接口契约
   - 输出：当前服务的上下游关系、已有接口签名、公共组件引用

2. **知识库补充规范约束**：
   - 执行 `python3 scripts/scan_kb.py --workdir {worktree_path}`
   - KB 定位到规范类文档：编码规范、MySQL 规范、安全规范、日志规范、Apollo 规范
   - 公共组件文档：`must_reuse` / `prefer_reuse` 命中后读使用指南

   **若 MCP 不可用，立即终止，不允许降级到本地副本或内置规则。**

### Step 0d — Worktree 创建

**dev-workflow 模式**：每个服务独立 worktree，命名 `feature-{日期}-{需求简称}`。
**独立模式**：如果当前已在 feature 分支上，跳过 worktree 创建。否则创建 worktree。

### Step 0e — GitNexus 调用链查询

查询当前服务涉及的调用链，缓存结果；不可用时记录后继续，不阻断。

### Step 0f — 依赖版本对齐

```bash
python3 scripts/align_deps.py \
  --shared-kb-dir {shared_kb_dir} \
  --path {worktree_path}
```

确保公共组件版本与知识库一致，最多 2 轮修复。

---

## Phase 1: Walking Skeleton

### 核心原则

骨架阶段的目标：**所有文件存在、所有依赖注入正确、所有模块编译通过、所有端点可调用（返回固定值或抛 Unsupported）**。

骨架阶段**不写**：
- 业务逻辑
- 数据库查询
- 上游服务调用
- 异常分支处理

### Step 1.1 — 创建文件骨架

按技术方案接口定义，创建以下文件：

| 层次 | 文件 | 骨架内容 |
|------|------|---------|
| Controller | `XxxController.java` | `@PostMapping` 端点签名完整，方法体调用 Service 后返回固定值或抛 `new BizException("TODO")` |
| Service 接口 | `XxxService.java` | 方法签名完整 |
| Service Impl | `XxxServiceImpl.java` | 方法体 `return null` 或 `throw new UnsupportedOperationException()` |
| DTO/Req/Res | `XxxParam.java` 等 | 字段完整，Lombok `@Data` |
| Config | `XxxConfig.java` | `@Value` 注入字段完整，默认值正确 |
| Client | `XxxClient.java` | `@Service`，方法签名完整，方法体 `return null` |

### Step 1.2 — 依赖注入与配置

- 所有 `@Resource` / `@Autowired` 注入字段已声明
- Apollo `@Value` 配置项已定义（含默认值）
- Maven/Gradle 模块间依赖已添加

### Step 1.3 — 编译验证

在 worktree 目录执行 `mvn compile`（或 `gradle compileJava`），必须通过。最多 3 轮修复。

### Step 1.4 — Git Commit（骨架 checkpoint）

```bash
git add -A && git commit -m "feat: walking skeleton（{服务名}）"
```

骨架是可编译的独立 checkpoint，便于后续 Phase 2 逐功能 commit 时 diff 清晰。

### Step 1.5 — 产出功能点状态表

编译通过后，按技术方案功能点拆分，产出初始状态表。格式：

```
| #   | 功能点              | 状态 | 说明                  |
|-----|--------------------|------|-----------------------|
| F-01| apply + checkAsync | ✅   | 骨架即完整（校验逻辑）  |
| F-02| handleSubTask code8 | 🔶  | 骨架就绪，展开逻辑待实现 |
| F-03| handleSubTask code9 | 🔶  | 骨架就绪，展开逻辑待实现 |
| F-04| preview             | 🔶  | 端点已通，上游查询待实现 |
| F-05| 单元测试             | ❌  | 未开始                 |
```

**规则**：
- 纯校验逻辑（如 `checkAsyncApply`）通常骨架即完整，可直接标 ✅
- 涉及外部调用、复杂业务逻辑的方法标 🔶
- 一个功能点一行，禁止合并多行

**向用户展示此表并确认**后才进入 Phase 2。

---

## Phase 2: TDD Flesh

按功能点逐个执行。每次只做一个功能点。

### Step 2.1 — 选一个 🔶 功能点

向用户汇报当前进度和即将开始的功能点，**默认连续执行无需用户逐项确认**：

```
🔶 开始实现 F-03 handleSubTask code9（标的维度展开）
   涉及文件：CombinedContractDownloadServiceImpl.java
   外部依赖：LoanDetailClient, ContractDownloadServiceImpl
   进度：3/7 功能点已完成
```

以下情况暂停等待用户确认：
- 修改共享接口签名（影响其他服务）
- 涉及数据库 DDL 变更
- 可能影响已有功能的行为

### Step 2.2 — 写测试（红灯）

先写测试用例：
- 正常路径：Mock 外部依赖，验证核心流程
- 边界条件：空输入、null、超限
- 异常分支：外部调用失败、数据异常

测试放 `src/test/java/` 对应包路径下。使用 JUnit4 + Mockito（对齐项目现有依赖，参见 `pom.xml` 中的 `mockito.version`）。

### Step 2.3 — 补实现

把 Step 1 的骨架方法体替换为完整逻辑：
- 参数校验
- 外部服务调用
- 业务逻辑
- 异常处理
- 日志

### Step 2.4 — 跑测试 → 绿灯

`mvn test -Dtest="XxxTest"`，必须全绿。

### Step 2.5 — 更新状态表

`🔶` → `⏳`（待核查），更新说明列。

### Step 2.6 — 重复

直到所有功能点 ⏳ 或 ✅（纯校验类已在 Phase 1 标 ✅ 的跳过）。

---

## Phase 3: Code Verification

**由 Leader 自己执行，不得委托子 Agent。**

### Step 3.1 — 读代码核查

对状态表中每个 ⏳ 功能点，读对应方法体：

```
检查项：
1. 方法体非空（不是空方法）
2. 非 return null
3. 非 throw UnsupportedOperationException
4. 非 echo 骨架（如只返回入参字段不做实际查询）
```

**纯校验逻辑豁免**：Phase 1 标注"骨架即完整"直接标 ✅ 的功能点（如 `checkAsyncApply`），检查方法体有实际校验逻辑即可，不强求独立测试类。

发现差距：`⏳` → 回退 `🔶`，记录到"已知缺口"，回到 Phase 2 补实现。
核查通过：`⏳` → `✅`。

### Step 3.2 — 全量编译 + 测试

```bash
mvn compile && mvn test
```

确保所有测试全绿。测试失败 → 最多 3 轮修复 → 仍失败则标记 `blocked`。

### Step 3.3 — 最终状态确认

向用户展示最终状态表，确认所有功能点状态正确。

---

## Phase 4: Summary & Report

### Step 4.1 — 生成汇总报告

**dev-workflow 模式**：输出到 `workflow/{需求名称}/04-开发编码.md`
**独立模式**：输出到 `{项目根目录}/coding-report-{日期}.md`

报告包含：
- 功能点状态表（最终版，含 ↩ 延后项清单）
- 各服务 commit hash
- 编译结果
- 测试结果

### Step 4.2 — 写入小结

在报告末尾追加 4-bullet 小结：

```markdown
## 小结

- 产出: {文件清单}
- 阻塞: {无，或简述}
- 已知缺口: {状态为 🔶 或 ⏳ 的功能点列表，说明具体缺什么。无则写"无"}
- 交接: {一句话，下一阶段必须知道的}
```

"已知缺口"字段必须如实填写。`↩` 延后项不在已知缺口中（已明确延后，出现于延后项清单）。

### Step 4.3 — 中间产物清理

清理各 worktree 目录下的 `.coding-*.json` 中间文件。保留最终报告和代码改动。任一步骤失败时保留对应服务现场，不清理。

---

## 功能点状态表维护规则

1. **每次状态变化立即更新**（🔶→✅、发现缺口回退等）
2. **🔶 必须说明具体缺口**（如"上游查询未实现"而非"未完成"）
3. **禁止将 🔶 项合并为"核心完成"** — 每个功能点独立一行
4. **Phase 3 核查后必须重新确认状态表**

---

## 复用约定

本 skill 有自己的 `scripts/` 目录。编排逻辑由 SKILL.md 自身驱动（Claude 执行），不依赖外部 workflow 脚本。

**自有脚本**（`scripts/` 目录）：
| 脚本 | 用途 | Phase |
|------|------|-------|
| `generate_report.py` | 生成 4-bullet 小结 + 功能点状态表 + 已知缺口 | Phase 4 |

`scan_kb.py`、`align_deps.py`、`kb_utils.py` 原为指向本机其他目录的链接，目标已不存在，本仓库不附带。知识库扫描和依赖对齐按本文件正文由调用方在本地完成。

以下操作由 Claude 直接执行，不走脚本：
- 编译验证：`mvn compile`（Phase 1.3 / 3.2）
- 单元测试：`mvn test`（Phase 2.4 / 3.2）
- 骨架生成：Claude 按技术方案创建 Java 文件（Phase 1.1）
- TDD 补全：Claude 写测试 + 补实现（Phase 2.2-2.4）
- 代码核查：Claude 读方法体验证（Phase 3.1）
- Git 操作：`git commit` / `git worktree`（Phase 1.4 / 0d）

**不使用的旧脚本**（与骨架优先哲学冲突）：
- `run_workflow.py` — 硬编码 TDD 优先阶段顺序
- `generate_code_skeleton.py` — 只生成 JSON 计划，不创建实际 Java 文件
- `summarize_report.py` — 旧格式报告，无 4-bullet 小结

## 文件索引

- 骨架阶段详细指南：[references/walking-skeleton-guide.md](references/walking-skeleton-guide.md)
- 完整工作流说明：[references/workflow.md](references/workflow.md)
- Worktree 操作指南：[references/worktree-guide.md](references/worktree-guide.md)
- 报告模板：[assets/coding-report-template.md](assets/coding-report-template.md)
