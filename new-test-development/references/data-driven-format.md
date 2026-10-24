# 数据驱动测试格式规范

本文档定义项目测试数据文件（`data/*.md`）的格式规范，以及与之配套的 StreamLoader 数据加载器的使用方式。

---

## 1. 核心概念

测试数据与测试执行器分离：
- **数据文件**（`data/*.md`）：存放所有测试用例的输入/输出参数，纯数据，无逻辑。
- **数据加载器**（`script/unit_test_data_loader.py`）：StreamLoader，基于状态机解析 Markdown，供各层测试执行器调用。
- **执行器文件**（`tests/{unit|api|functional}/*.py`）：从数据文件加载参数，使用 `@pytest.mark.parametrize` 驱动执行。

---

## 2. 数据文件格式规范

### 2.1 文件路径映射

| 测试层 | 数据文件 | CLI 别名 |
|--------|----------|----------|
| 单元测试 | `data/unit_test_data.md` | `unit` |
| 接口测试 | `data/api_test_data.md` | `api` |
| 功能测试 | `data/functional_test_data.md` | `functional` |

### 2.2 通用格式规则

```markdown
# 注释行（以 # 开头，解析时跳过）

# ─── 函数定义行（标记一组测试的开始）─────────
[ClassName_methodName] col1 | col2 | col3 | bug_reason

# 数据行
[TC-Xxx] {python_dict} | value | value | bug_reason_string
```

**两种行的识别规则**（StreamLoader 状态机判断依据）：
- **函数定义行**：以 `[` 开头，**不含** `{`，后跟列头，`|` 分隔
- **数据行**：以 `[TC-` 开头，**必含** `{`，值由 `|` 分隔

**关键约束**：
- 值使用 **Python 字面量**（`True`/`False`/`None`），**不是** JSON（`true`/`false`/`null`）
- 字典和列表由 `ast.literal_eval` 解析，支持嵌套结构
- `bug_reason` 是最后一列，纯字符串，失败时供 AI 快速定位根因
- 中文字符在字符串值中完全支持（UTF-8 编码）

---

## 3. 各层数据格式详解

### 3.1 单元测试数据格式

**列定义**：根据被测方法签名确定，最后一列固定为 `bug_reason`

**通用格式**：
```markdown
[TestClassName_methodName] input_data | expected | bug_reason
[TC-Uxx] {"param1": value, "param2": value} | expected_value | 失败时最可能的原因描述
```

**多列格式**（当有多个期望值或控制字段时）：
```markdown
[TestCalcNext_calcNext] input_data | expected | expect_raises | bug_reason
[TC-U043] {"base": "2026-04-01 10:00:00", "value": 1, "unit": "hour"} | "2026-04-01 11:00:00" | False | hour 对应秒数错误（应为 3600）
[TC-U046] {"base": "2026-04-01 10:00:00", "value": 1, "unit": "week"} | None | True | 非法 unit 未抛 ManagementException
```

**特殊 expected 值（哨兵值）**：
- `"non_empty"` → 执行器检查结果非空字符串
- `"future_datetime"` → 执行器只校验格式（长度 19、含 `-` 和 `:`）
- `"tempdir"` → 执行器创建临时目录后扫描
- `"__exists__"` → 执行器只检查字段存在，不比较值

**执行器模板（单元测试）**：
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
        result = target_function(d["param1"], d["param2"])
        assert result == case["expected"]
```

---

### 3.2 接口测试数据格式

**固定列定义**：
```markdown
[TestClassName_methodName] input_data | expected_status | mock_type | assert_spec | bug_reason
```

**列说明**：

| 列名 | 类型 | 说明 |
|------|------|------|
| `input_data` | dict | 必含 `url`；可含 `method`（默认GET）、`body`、`headers` |
| `expected_status` | int | HTTP 状态码，如 200/201/400/403/404/422 |
| `mock_type` | str | 映射到执行器内的 mock 注册表；`"none"` 表示无需 mock |
| `assert_spec` | dict | 断言规格，见下方格式说明 |
| `bug_reason` | str | 失败时最可能的根因 |

**assert_spec 三种断言格式**：
```python
# 1. 普通相等断言（点分路径取值）
{"success": True, "data.schedule_id": "sch_new"}

# 2. 字段存在性断言
{"data_has_keys": ["items", "page", "summary"]}

# 3. 前缀检查断言（key 以 "startswith:" 开头）
{"startswith:data.task.workspace_path": ".../"}
```

**示例数据行**：
```markdown
[TestListSchedules_listSchedules] input_data | expected_status | mock_type | assert_spec | bug_reason
[TC-A012] {"url": "/management/api/schedules", "method": "GET"} | 200 | "sched_list_ok" | {"success": True, "data_has_keys": ["items", "page"]} | list_schedules 未被调用或响应结构缺少必要字段
[TC-A013] {"url": "/management/api/schedules?page=0", "method": "GET"} | 422 | "none" | {} | FastAPI 参数校验未拦截 page=0
[TC-A024] {"url": "/api/schedules", "method": "POST", "body": {"schedule_name": "X"}, "headers": {"X-Role": "manager"}} | 403 | "none" | {"detail.error.code": "permission_denied"} | MANAGER 角色权限检查未生效
```

**执行器模板（接口测试）**：
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

# --- 通用助手函数 ---

def _do_request(input_data: dict):
    method = input_data.get("method", "GET").upper()
    url, body, headers = input_data["url"], input_data.get("body"), input_data.get("headers", {})
    if method == "GET":    return client.get(url, headers=headers)
    if method == "POST":   return client.post(url, json=body, headers=headers)
    if method == "PUT":    return client.put(url, json=body, headers=headers)
    if method == "PATCH":  return client.patch(url, json=body, headers=headers)

def _get_path(body, path):
    for p in path.split("."):
        body = body.get(p) if isinstance(body, dict) else None
    return body

def _check_assert_spec(body: dict, spec: dict):
    for key, expected in spec.items():
        if key == "data_has_keys":
            data = body.get("data") or {}
            for k in expected:
                assert k in data
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

# --- 测试类 ---

class TestListSchedules:
    _TARGET = "src.schedule.services.ScheduleService.list_schedules"

    @pytest.mark.parametrize("case", loader.fetch("TestListSchedules_listSchedules"), ids=lambda c: c["case_id"])
    def test_listSchedules_shouldMatchExpected(self, case):
        from src.schedule.schemas import ScheduleListResult
        returns_map = {"sched_list_ok": lambda: ScheduleListResult(**MOCK_LIST_RESULT)}
        with _maybe_mock(self._TARGET, returns_map, {}, case["mock_type"]):
            resp = _do_request(case["input_data"])
        assert resp.status_code == case["expected_status"]
        _check_assert_spec(resp.json(), case["assert_spec"])
```

**Mock 注册表规则**：
- 每个测试类对应一个服务方法（`_TARGET`）
- `returns_map`：mock_type → 返回值工厂函数（lambda）
- `raises_map`：mock_type → 异常工厂函数（lambda）
- mock_type `"none"` 跳过 patch，直接调用路由（用于权限拦截等场景）

---

### 3.3 功能测试数据格式

**固定列定义**：
```markdown
[TestClassName_methodName] input_data | expected | bug_reason
```

**列说明**：

| 列名 | 类型 | 说明 |
|------|------|------|
| `input_data` | dict | 场景配置参数，含 `schedule_preset`（预设名）、操作参数等 |
| `expected` | dict | 最终状态断言值，执行器按字段名分发断言 |
| `bug_reason` | str | 失败时最可能的根因 |

**schedule_preset 预设机制**：
- 定义在执行器顶部的 `_SCHEDULE_PRESETS` 字典中
- 预设名如 `"recurring_standard"`、`"one_time_standard"`
- `schedule_override` 字段可覆盖预设中的个别字段
- 执行器通过 `_resolve_body(input_data)` 合并预设与覆盖

**示例数据行**：
```markdown
[TestAuditorMasking_masking] input_data | expected | bug_reason
[TC-F007] {"schedule_preset": "recurring_standard", "get_role": "auditor"} | {"project_path_masked": True, "context_token_masked": True} | AUDITOR 角色的路径和 token 未被脱敏
[TC-F008] {"schedule_preset": "recurring_standard", "get_role": "operator"} | {"project_path": "/work/proj-a", "context_token": "secret-tok"} | OPERATOR 角色被错误脱敏
```

**执行器模板（功能测试）**：
```python
import os
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, delete
from script.unit_test_data_loader import StreamLoader

_DATA = os.path.join(os.path.dirname(__file__), "..", "..", "data", "functional_test_data.md")
loader = StreamLoader(os.path.abspath(_DATA))

# 测试引擎（模块级，StaticPool 保证同一连接）
_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
from src.models import ModelA, ModelB  # 导入所有表模型触发 metadata 注册
SQLModel.metadata.create_all(_engine)

@contextmanager
def _get_session():
    with Session(_engine, expire_on_commit=False) as session:
        try: yield session; session.commit()
        except Exception: session.rollback(); raise

@pytest.fixture(autouse=True)
def patch_db(monkeypatch):
    monkeypatch.setattr("src.database.config.get_session", _get_session)
    # 按需添加其他模块的 patch
    monkeypatch.setattr("src.database.config.engine", _engine)
    yield
    with Session(_engine) as s:
        s.exec(delete(ModelB)); s.exec(delete(ModelA)); s.commit()

@pytest.fixture()
def client(patch_db):
    from src.app_entry import app
    with TestClient(app, raise_server_exceptions=True) as c: yield c

# 预设定义
_SCHEDULE_PRESETS = {
    "recurring_standard": {...},
    "one_time_standard": {...},
}

def _resolve_body(input_data: dict) -> dict:
    base = dict(_SCHEDULE_PRESETS[input_data["schedule_preset"]])
    base.update(input_data.get("schedule_override", {}))
    return base

class TestAuditorMasking:
    @pytest.mark.parametrize("case", loader.fetch("TestAuditorMasking_masking"), ids=lambda c: c["case_id"])
    def test_masking_shouldRespectRole(self, client, case):
        d, exp = case["input_data"], case["expected"]
        # 创建计划，按角色查询，断言脱敏/不脱敏
        ...
```

---

## 4. StreamLoader 数据加载器规范

### 4.1 文件路径

```
script/unit_test_data_loader.py
```

### 4.2 核心接口

```python
class StreamLoader:
    def __init__(self, file_path: str): ...
    def fetch(self, target_func: str, target_case_id: str | None = None) -> list[dict]: ...
```

返回格式：
```python
[
    {"case_id": "TC-U043", "input_data": {...}, "expected": "...", "bug_reason": "..."},
    ...
]
```

### 4.3 CLI 用法

```bash
# 按别名查询
python script/unit_test_data_loader.py -f unit TestCalcNext_calcNext
python script/unit_test_data_loader.py -f api TestListSchedules_listSchedules
python script/unit_test_data_loader.py -f functional TestAuditorMasking_masking

# 精准查询单条用例
python script/unit_test_data_loader.py -f unit TestCalcNext_calcNext TC-U043

# 自定义文件路径
python script/unit_test_data_loader.py -f /path/to/custom.md TestSomething_method
```

### 4.4 加载器不存在时的创建规范

若 `script/unit_test_data_loader.py` 不存在，按以下模板创建：

```python
"""
测试数据加载器（单元 / 接口 / 功能测试通用）

支持两种调用方式：
1. 代码调用: StreamLoader(file_path).fetch(func_key)
2. 命令行:
     python unit_test_data_loader.py [-f {unit|api|functional|<path>}] <func_key> [case_id]
"""
import ast
import os
import sys

class StreamLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def fetch(self, target_func: str, target_case_id: str | None = None) -> list[dict]:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"找不到数据文件: {self.file_path}")
        results, in_target_block, headers = [], False, []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if line.startswith(f"[{target_func}]") and "{" not in line:
                    in_target_block = True
                    headers = [h.strip() for h in line.replace(f"[{target_func}]", "").split("|")]
                    continue
                if in_target_block:
                    if line.startswith("[") and "{" not in line: break
                    if line.startswith("[") and "{" in line:
                        id_end = line.find("]")
                        case_id = line[1:id_end]
                        if target_case_id and case_id != target_case_id: continue
                        results.append(self._parse_line(line, id_end, headers))
                        if target_case_id and case_id == target_case_id: break
        return results

    def _parse_line(self, line, id_end, headers):
        case_id = line[1:id_end]
        values = [v.strip() for v in line[id_end + 1:].strip().split("|")]
        case_data = {"case_id": case_id}
        for i, key in enumerate(headers):
            if i < len(values):
                try: case_data[key] = ast.literal_eval(values[i])
                except Exception: case_data[key] = values[i]
        return case_data

_DATA_FILE_ALIASES = {
    "unit": "unit_test_data.md",
    "api": "api_test_data.md",
    "functional": "functional_test_data.md",
}

def _resolve_data_file(file_arg):
    name = _DATA_FILE_ALIASES.get(file_arg)
    path = os.path.join(os.path.dirname(__file__), "..", "data", name) if name else file_arg
    return os.path.abspath(path)

def main():
    args = sys.argv[1:]
    file_alias = "unit"
    if args and args[0] == "-f":
        if len(args) < 3: print("用法: python unit_test_data_loader.py [-f {unit|api|functional|<path>}] <func_key> [case_id]"); sys.exit(1)
        file_alias, args = args[1], args[2:]
    if not args: print("缺少 func_key 参数"); sys.exit(1)
    func_key, case_id = args[0], (args[1] if len(args) > 1 else None)
    loader = StreamLoader(_resolve_data_file(file_alias))
    cases = loader.fetch(func_key, target_case_id=case_id)
    if not cases: print(f"未找到: [{func_key}]"); sys.exit(1)
    for case in cases:
        cid = case.pop("case_id")
        print(f"[{cid}] {case}")

if __name__ == "__main__":
    main()
```

同时确保 `script/__init__.py` 存在（空文件），使 `script` 包可被 import。

---

## 5. 数据文件生成规则

### 5.1 何时生成

- **NTD-S1（单元测试清单确认后）**：同步生成 `data/unit_test_data.md`
- **NTD-S2（接口测试清单确认后）**：同步生成 `data/api_test_data.md`
- **NTD-S3（功能测试清单确认后）**：同步生成 `data/functional_test_data.md`
- 若同名文件已存在：**追加**新增的函数块，不覆盖已有数据

### 5.2 函数键命名规则

```
[ClassName_methodName]
```

- `ClassName`：与执行器中的测试类名一致（如 `TestCalcNext`）
- `methodName`：与执行器中 `loader.fetch()` 的参数一致（如 `calcNext`）
- 同一个测试类的不同方法对应不同函数键（如 `TestScheduleStatusLifecycle_statusSwitch` 和 `TestScheduleStatusLifecycle_completedLock`）

### 5.3 bug_reason 编写指引

- 简洁描述"测试失败时最可能的原因"
- 格式：`<缺失或错误的内容> 导致 <具体的失败现象>`
- 示例：`_TASK_STATUS_LABELS 缺少 QUEUED 或标签值拼写错误`
- 示例：`one_time 且 trigger_at 为 None 时未抛 ManagementException`
- 长度控制在 30 字以内，便于在终端/报告中一行显示
