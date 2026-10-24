# ============================================================
# 用户指令
# ============================================================
用户指令:
    - "编写测试代码"

# ============================================================
# 指令名称
# ============================================================
指令名称: "编写测试代码"

# ============================================================
# 任务描述
# ============================================================
任务描述: "读取单元测试、接口测试、功能测试的三份【测试清单】，依据《测试代码规范》，将其转换为可执行的自动化测试代码，并进行完备性自检。"

# ============================================================
# 前置条件_信息收集与澄清
# ============================================================
前置条件_信息收集与澄清:
  - 动作: "引用"
    内容: "单元测试清单文件"
    参数: "$测试清单"
    必要性: "必须"
  - 动作: "引用"
    内容: "接口测试清单文件"
    参数: "$测试清单"
    必要性: "必须"
  - 动作: "引用"
    内容: "功能测试清单文件"
    参数: "$测试清单"
    必要性: "必须"

# ============================================================
# 任务内容
# ============================================================
任务内容: |
  请扮演资深测试开发工程师 (SET)，严格遵循 `${测试代码规范}`，并结合项目现有测试资产基线，将自然语言编写的 `${测试清单}` 转换为高质量的新增功能测试代码。

  ## Step 1: 深度理解规范与上下文
  
  **目标**: 内化测试代码规范，构建准确的编码上下文。
  
  **执行动作**:
  - **规范解析**: 仔细阅读 `${测试代码规范}`，明确以下关键点：
    - 目录结构（源码 vs 测试代码的对应关系）。
    - 命名规则（类名后缀、方法名格式、变量命名）。
    - 编码风格（缩进、注释、断言库选择）。
    - 依赖管理（Mock 框架、工具类库）。
  - **上下文映射**: 
    - 确定被测对象（类/接口）在项目中的位置。
    - 识别测试清单类型（单元/接口/功能），加载对应的思维模型。
    - 识别现有测试目录、公共 fixture、builder、mock 工具和断言辅助类，优先复用。

  ---

  ## Step 1.5: 数据加载器检查（先于代码生成，不可跳过）

  **执行动作**:
  - 检查 `script/unit_test_data_loader.py` 是否存在。
  - **若不存在**：按《数据驱动格式规范》第 4.4 节模板创建；同时创建 `script/__init__.py`（空文件）。
  - **若已存在**：确认包含 `StreamLoader` 类和 `-f` CLI 参数支持，不满足则补充。
  - 确认 `data/unit_test_data.md`、`data/api_test_data.md`、`data/functional_test_data.md` 三个数据文件已由 NTD-S1~S3 生成。

  ---

  ## Step 2: 单元测试代码生成 (Unit Test)
  **执行动作**:
  - **读取用例文件**：`data/unit_test_data.md`（StreamLoader 数据文件，不是清单 md）
  - **数据驱动强制**：每个测试类使用 `loader.fetch("ClassName_methodName")` 加载用例，通过 `@pytest.mark.parametrize` 驱动，**禁止在测试代码中硬编码用例数据**。
  - **Mock 策略**: 依据规范，对所有外部依赖（DB/RPC/File）进行 Mock/Stub，确保测试纯粹性（Pure Function）。
  - **逻辑映射**: 将数据行中的 `input_data` → `Arrange`，调用被测方法 → `Act`，对比 `expected` → `Assert`。
  - **边界覆盖**: Null 值、边界值、异常抛出用例通过 `expect_raises` 列或特殊 expected 哨兵值区分。
  - **验证点**: 确保清单中每个 TC-U* 编号都有对应的数据行，且被参数化覆盖。

  **单元测试执行器模板（Python）**：
  ```python
  import os
  import pytest
  from script.unit_test_data_loader import StreamLoader

  _DATA = os.path.join(os.path.dirname(__file__), "..", "..", "data", "unit_test_data.md")
  loader = StreamLoader(os.path.abspath(_DATA))

  class TestClassName:
      @pytest.mark.parametrize("case", loader.fetch("TestClassName_methodName"), ids=lambda c: c["case_id"])
      def test_method_shouldMatchExpected(self, case):
          d = case["input_data"]
          if case.get("expect_raises"):
              with pytest.raises(ExpectedException):
                  target_function(d["param1"], d["param2"])
          else:
              result = target_function(d["param1"], d["param2"])
              assert result == case["expected"]
  ```

  ---

  ## Step 3: 接口测试代码生成 (API Test)
  **执行动作**:
  - **读取用例文件**：`data/api_test_data.md`（StreamLoader 数据文件）
  - **数据驱动强制**：每个测试类使用 `loader.fetch("ClassName_methodName")` 加载用例，通过 `@pytest.mark.parametrize` 驱动，**禁止硬编码用例数据**。
  - **三大助手函数**（必须实现，复用于同文件所有类）：
    - `_do_request(input_data)` — 按 method 分发请求
    - `_check_assert_spec(body, spec)` — 支持点分路径 / `data_has_keys` / `startswith:` 三种断言
    - `_maybe_mock(target, returns_map, raises_map, mock_type)` — 条件性 patch 上下文管理器
  - **Mock 注册表**：每个测试类定义 `returns_map`（正常返回）和 `raises_map`（异常抛出），键为数据文件中的 `mock_type` 字符串。
  - **验证点**: `assert resp.status_code == case["expected_status"]` + `_check_assert_spec(resp.json(), case["assert_spec"])`。

  **接口测试执行器模板（Python）**：
  ```python
  import os
  from contextlib import contextmanager
  from unittest.mock import patch
  import pytest
  from fastapi.testclient import TestClient
  from src.app_entry import app
  from script.unit_test_data_loader import StreamLoader

  client = TestClient(app, raise_server_exceptions=False)
  _DATA = os.path.join(os.path.dirname(__file__), "..", "..", "data", "api_test_data.md")
  loader = StreamLoader(os.path.abspath(_DATA))

  def _do_request(d):
      m = d.get("method", "GET").upper()
      url, body, h = d["url"], d.get("body"), d.get("headers", {})
      if m == "GET":   return client.get(url, headers=h)
      if m == "POST":  return client.post(url, json=body, headers=h)
      if m == "PUT":   return client.put(url, json=body, headers=h)
      if m == "PATCH": return client.patch(url, json=body, headers=h)

  def _get_path(body, path):
      for p in path.split("."):
          body = body.get(p) if isinstance(body, dict) else None
      return body

  def _check_assert_spec(body, spec):
      for key, expected in spec.items():
          if key == "data_has_keys":
              data = body.get("data") or {}
              for k in expected: assert k in data
          elif key.startswith("startswith:"):
              actual = _get_path(body, key[len("startswith:"):])
              assert isinstance(actual, str) and actual.startswith(str(expected))
          else:
              assert _get_path(body, key) == expected

  @contextmanager
  def _maybe_mock(target, returns_map, raises_map, mock_type):
      if not mock_type or mock_type == "none":
          yield None; return
      with patch(target) as m:
          if mock_type in raises_map:   m.side_effect = raises_map[mock_type]()
          elif mock_type in returns_map: m.return_value = returns_map[mock_type]()
          yield m

  class TestListSchedules:
      _TARGET = "src.schedule.services.ScheduleService.list_schedules"

      @pytest.mark.parametrize("case", loader.fetch("TestListSchedules_listSchedules"), ids=lambda c: c["case_id"])
      def test_listSchedules_shouldMatchExpected(self, case):
          from src.schedule.schemas import ScheduleListResult
          returns_map = {"sched_list_ok": lambda: ScheduleListResult(**MOCK_LIST)}
          with _maybe_mock(self._TARGET, returns_map, {}, case["mock_type"]):
              resp = _do_request(case["input_data"])
          assert resp.status_code == case["expected_status"]
          _check_assert_spec(resp.json(), case["assert_spec"])
  ```

  ---

  ## Step 4: 功能测试代码生成 (E2E Test)

  **执行动作**:
  - **读取用例文件**：`data/functional_test_data.md`（StreamLoader 数据文件）
  - **数据驱动强制**：每个测试方法使用各自的函数键加载数据，通过 `@pytest.mark.parametrize` 驱动。
  - **预设机制**：在执行器顶部定义 `_SCHEDULE_PRESETS` 字典；通过 `_resolve_body(input_data)` 合并 `schedule_preset` + `schedule_override` 生成完整请求体。
  - **DB 隔离**：使用 `StaticPool` SQLite 内存引擎 + `expire_on_commit=False` + `autouse fixture` 自动清理，保证测试间不污染。
  - **流程编排**: 将 `input_data` 中的场景参数提取后驱动测试步骤，每步结果用 `expected` 字段中的值断言。
  - **副作用验证**: 触发 A 后检查 B 的状态（`expected["b_last_task_id"]` 等），确保副作用隔离。

  **功能测试 DB 隔离基础设施（必须包含）**：
  ```python
  from sqlalchemy.pool import StaticPool
  from sqlmodel import Session, SQLModel, create_engine, delete
  from contextlib import contextmanager

  _engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
  from src.models import TableA, TableB  # 触发 metadata 注册
  SQLModel.metadata.create_all(_engine)

  @contextmanager
  def _get_session():
      with Session(_engine, expire_on_commit=False) as session:
          try: yield session; session.commit()
          except Exception: session.rollback(); raise

  @pytest.fixture(autouse=True)
  def patch_db(monkeypatch):
      monkeypatch.setattr("src.database.config.get_session", _get_session)
      monkeypatch.setattr("src.database.config.engine", _engine)
      yield
      with Session(_engine) as s:
          s.exec(delete(TableB)); s.exec(delete(TableA)); s.commit()

  @pytest.fixture()
  def client(patch_db):
      from src.app_entry import app
      with TestClient(app, raise_server_exceptions=True) as c: yield c
  ```

  ---

  ## Step 5: 完备性自检与优化

  **目标**: 确保"清单"与"代码"严格一致，无遗漏，且符合高质量标准。

  **执行动作**:
  1. **双向核对**: 遍历 Markdown 清单中的每一个 Case ID，检查是否存在对应的 `@Test` 方法。
  2. **断言检查**: 扫描所有生成的测试方法，确保**至少包含一个有效断言**（Assert/Verify）。
  3. **规范扫描**: 检查目录名（英文 `unit/`/`api/`/`functional/`）、文件名（`test_{ClassName}.py` 等）、方法名是否符合 `${测试代码规范}`。
  4. **代码优化**: 移除冗余代码，提取公共逻辑，确保代码清晰易读。

  **产出**:
  - 符合规范的测试代码文件（目录: `tests/unit/`, `tests/api/`, `tests/functional/`）。
  - 简要的生成摘要（包含已生成用例数/总用例数）。

  ---

  ## Step 6: 并行测试执行 + 测试报告生成（NTD-S6）

  **目标**: 执行所有测试并生成统一的测试报告。

  **执行动作**:

  ### 6.1 同时启动三个并行 Agent（不等待，立即并发）

  ```
  Agent-Unit      → 执行 tests/unit/ 下的所有测试
  Agent-API       → 执行 tests/api/ 下的所有测试
  Agent-Functional → 执行 tests/functional/ 下的所有测试
  ```

  每个 Agent 的任务：
  - 运行对应目录的测试套件（命令见各语言示例）。
  - 收集：总用例数、通过数、失败数、跳过数、总耗时。
  - 收集每条失败用例的：TC 编号、测试方法名、失败原因（assertion message / exception）、堆栈摘要（前3行）。
  - 以结构化 JSON 格式返回结果供汇总。

  **各语言运行命令参考**：
  ```bash
  # Python (pytest)
  pytest tests/unit/ -v --tb=short --json-report --json-report-file=unit_result.json
  pytest tests/api/ -v --tb=short --json-report --json-report-file=api_result.json
  pytest tests/functional/ -v --tb=short --json-report --json-report-file=functional_result.json

  # Java (Maven)
  mvn test -Dtest="unit/**" -Dsurefire.reportsDirectory=target/surefire-unit
  mvn test -Dtest="api/**" -Dsurefire.reportsDirectory=target/surefire-api
  mvn test -Dtest="functional/**" -Dsurefire.reportsDirectory=target/surefire-functional

  # Go
  go test ./tests/unit/... -v -json > unit_result.json
  go test ./tests/api/... -v -json > api_result.json
  go test ./tests/functional/... -v -json > functional_result.json
  ```

  ### 6.2 等待三个 Agent 全部完成后汇总

  收到全部三个 Agent 的结果后，执行以下汇总：
  - 合并通过/失败/跳过计数。
  - 提取所有失败用例。
  - 计算整体通过率。

  ### 6.3 生成测试报告

  将报告写入 `test_case/测试报告.md`，格式如下：

  ```markdown
  # 测试执行报告

  **执行时间**: {datetime}
  **项目**: {project_name}

  ---

  ## 执行概览

  | 层级 | 总用例 | 通过 | 失败 | 跳过 | 通过率 | 耗时 |
  |------|--------|------|------|------|--------|------|
  | 单元测试 | N | N | N | N | N% | Ns |
  | 接口测试 | N | N | N | N | N% | Ns |
  | 功能测试 | N | N | N | N | N% | Ns |
  | **合计** | N | N | N | N | N% | Ns |

  ---

  ## 失败用例明细

  ### 单元测试失败
  | TC编号 | 测试方法 | 失败原因 |
  |--------|---------|---------|
  | TC-U001 | test_xxx | AssertionError: expected True but got False |

  ### 接口测试失败
  （同上格式）

  ### 功能测试失败
  （同上格式）

  ---

  ## 根因分析与修复建议

  针对每个失败用例给出：
  - **根因**: 实现缺陷 / 测试数据问题 / 环境问题
  - **行动项**: 具体修复步骤

  ---

  ## 覆盖率（如工具支持）

  {coverage_summary}
  ```

# ============================================================
# 参考规范与模板
# ============================================================
参考规范与模板:
  - 资源名称: "测试代码规范"
    类型: "代码规范"
    说明: "遵循项目定义的测试代码目录结构和命名规则。"

# ============================================================
# 备注与最佳实践 (专家经验)
# ============================================================
备注与最佳实践:
  - "【命名即文档】 测试方法名应采用 `Should_ExpectedBehavior_When_State` (Java) 或 `test_condition_result` (Python) 格式，让代码可读性最大化。"
  - "【AAA 模式】 严格遵守 Arrange (准备) -> Act (执行) -> Assert (断言) 结构，用空行分隔这三部分。"
  - "【断言单一职责】 尽量在一个测试方法中只验证一个核心概念，若有多个维度的验证，请使用 `SoftAssert` 或拆分为多个测试方法。"
  - "【数据独立性】 严禁测试方法之间共享可变状态。每个测试运行前必须重置环境（使用 @BeforeEach / setUp）。"
  - "【Mock 适度】 单元测试 Mock 外部依赖，集成测试尽量少 Mock。如果 Mock 代码超过了测试逻辑代码，说明设计可能存在耦合过重。"
  - "【失败信息的艺术】 断言失败时，必须提供清晰的错误信息（Context），说明"期望是什么"以及"实际得到了什么"，方便快速排错。"
