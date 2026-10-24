# ============================================================
# 用户指令
# ============================================================
用户指令:
    - "接口测试"
    - "写接口测试"
    - "API测试"

# ============================================================
# 指令名称
# ============================================================
指令名称: "接口测试"

# ============================================================
# 任务描述
# ============================================================
任务描述: "遵循《测试思维框架》中的契约建模与1+N+M 模式，针对 API 接口生成包含参数校验、业务逻辑、安全越权的全维度测试清单及脚本。"

# ============================================================
# 前置条件_信息收集与澄清
# ============================================================
前置条件_信息收集与澄清:
  - 动作: "引用"
    内容: "服务接口文档"
    参数: "$API契约"
    必要性: "必须"
  - 动作: "引用"
    内容: "业务功能文档"
    参数: "$业务文档"
    必要性: "可选"

# ============================================================
# 任务内容
# ============================================================
任务内容: |
  请扮演资深测试工程师 (QA)，基于提供的 `${API契约}` 和 `${业务文档}`，并结合项目现有接口测试基线，严格遵循《测试思维框架》进行新增功能的接口测试设计与代码实现。

  ## Step 1: 接口列表提取

  **目标**: 从服务接口文档中提取承载新增能力的接口信息。

  **执行动作**:
  - 提取新增接口，以及承载新增能力的相关 Endpoint（URL、Method）
  - 提取每个接口的请求参数（类型、必填性、格式、范围、枚举值）
  - 提取响应结构（成功响应、异常响应码）
  - 识别业务规则（状态流转、数据守恒点）
  - 检查现有接口测试脚本、请求构造器和鉴权封装是否可复用

  ---

  ## Step 2: 测试清单生成

  **目标**: 基于《测试思维框架》，应用完整的思维链路为每个接口生成测试清单。

  **执行动作**:
  - 引用《测试思维框架》，应用其中的完整思维链路和方法论
  - 为每个接口系统性生成测试用例

  **产出**: 生成初版接口测试清单.md

  ---

  ## Step 3: 基于服务接口 Review 与补全

  **目标**: 对照新增能力涉及的服务接口列表和现有接口测试基线，自动审查测试清单的完备性。

  **执行动作**:
  1. **完整性检查**: 每个接口是否都生成了测试清单？
  2. **场景覆盖检查**:
     - 是否覆盖 1+N+M 所有场景？
     - 参数 >=3 时是否应用了 Pairwise？
     - 创建/更新类接口是否测试了幂等性？
     - 是否包含安全测试（SQL注入、XSS、越权）？
     - 新增接口与现有鉴权、幂等、错误码风格的衔接场景是否覆盖？
  3. **自动补全**: 发现缺失时，自动补充测试用例，更新清单。
  4. **迭代验证**: 重复检查-补全，直至完整覆盖。

  **产出**: 完善后的接口测试清单.md

  ---

  ## Step 4: AI 专业自审（必须执行，不可跳过）

  **目标**: 从资深测试工程师视角对初版清单做独立审查，发现遗漏并补全。

  **执行动作**:
  1. **Endpoint 覆盖检查**：对照接口文档，确认每个 Endpoint（URL + Method）都有对应清单。
  2. **1+N+M 检查**：每个接口是否满足：1个成功路径 + N个参数异常 + M个业务/安全异常？
  3. **安全对抗检查**：是否覆盖路径穿越、注入攻击、越权访问？
  4. **断言完整性检查**：是否包含状态码 + 响应体关键字段 + DB 状态三维断言？
  5. **参数组合检查**：参数 ≥ 3 个时是否应用了 Pairwise 组合？
  6. **补全**：发现遗漏自动补充，并标注 `[AI补全]` 便于人工复核。

  **产出规范**:
  - **产出文件**: `test_case/接口测试清单.md`（含 `[AI补全]` 标注项）
  - **产出位置**: `test_case/` 目录

  > **⏸ PAUSE — 输出清单摘要，等待人工确认后再进入下一步。**
  > 摘要格式：接口数 / 1+N+M 分布 / 安全覆盖情况 / AI补全项数

# ============================================================
# HTTP 测试具体断言模式
# ============================================================
HTTP断言模式:
  说明: "接口测试不仅校验 HTTP Status，必须覆盖响应体、Header 和数据库状态的完整验证"

  模式列表:
    - 维度: "状态码断言"
      必要性: "必须"
      示例: |
        .andExpect(status().isCreated())      // 201 创建成功
        .andExpect(status().isBadRequest())   // 400 参数异常
        .andExpect(status().isForbidden())    // 403 权限不足
        .andExpect(status().isNotFound())     // 404 资源不存在
        .andExpect(status().isConflict())     // 409 幂等冲突
      常见错误: "只校验 2xx，忽略不同异常场景应返回不同的 4xx"

    - 维度: "响应体关键字段断言"
      必要性: "必须"
      示例: |
        // 成功场景 - 校验业务字段
        .andExpect(jsonPath("$.orderId").exists())
        .andExpect(jsonPath("$.status").value("PENDING"))
        .andExpect(jsonPath("$.amount").value(100.00))

        // 异常场景 - 校验错误码和错误信息
        .andExpect(jsonPath("$.errorCode").value("MISSING_FIELD"))
        .andExpect(jsonPath("$.message").isNotEmpty())
      常见错误: "只校验 status code 不校验 body，导致错误码返回错误但测试通过"

    - 维度: "响应 Header 断言"
      必要性: "按需"
      示例: |
        .andExpect(header().exists("Location"))              // 201 返回资源地址
        .andExpect(header().string("Content-Type", "application/json"))
        .andExpect(header().exists("X-Request-Id"))          // 幂等 ID 回传
      常见错误: "忽略 Location header 的校验导致资源发现链路断裂"

    - 维度: "数据库状态断言"
      必要性: "必须（写操作）"
      示例: |
        // 创建接口 - 验证数据已持久化
        Order saved = orderRepo.findByOrderId(orderId);
        assertNotNull(saved);
        assertEquals("user123", saved.getUserId());
        assertEquals(OrderStatus.PENDING, saved.getStatus());

        // 删除接口 - 验证数据已移除
        assertTrue(orderRepo.findById(orderId).isEmpty());
      常见错误: "只校验 HTTP 响应不校验数据库，导致响应正确但数据未持久化"

    - 维度: "安全对抗断言"
      必要性: "必须（用户输入字段）"
      示例: |
        // SQL 注入 - 应被拦截
        String malicious = "' OR '1'='1";
        mockMvc.perform(post("/users")
            .content("{\"name\": \"" + malicious + "\"}"))
            .andExpect(status().isBadRequest());

        // XSS 注入 - 应被转义或拒绝
        String xss = "<script>alert('xss')</script>";
        mockMvc.perform(post("/comments")
            .content("{\"text\": \"" + xss + "\"}"))
            .andExpect(status().isBadRequest());

        // 水平越权 - 应被禁止
        mockMvc.perform(get("/orders/" + otherUserOrderId)
            .header("Authorization", "Bearer " + userAToken))
            .andExpect(status().isForbidden());
      常见错误: "只测试 Happy Path，上线后被恶意请求攻破"

    - 维度: "幂等性断言"
      必要性: "必须（创建/更新类接口）"
      示例: |
        // 使用相同 request-id 重复调用，应返回相同结果
        String requestId = UUID.randomUUID().toString();
        String body = "{\"userId\": \"user1\", \"amount\": 100}";

        // 第一次调用 - 正常创建
        MvcResult first = mockMvc.perform(post("/orders")
            .header("X-Request-Id", requestId)
            .content(body))
            .andExpect(status().isCreated())
            .andReturn();
        String orderId1 = JsonPath.read(first.getResponse().getContentAsString(), "$.orderId");

        // 第二次调用 - 相同 request-id，应幂等返回
        MvcResult second = mockMvc.perform(post("/orders")
            .header("X-Request-Id", requestId)
            .content(body))
            .andExpect(status().isOk())  // 或 201，取决于接口设计
            .andReturn();
        String orderId2 = JsonPath.read(second.getResponse().getContentAsString(), "$.orderId");

        assertEquals(orderId1, orderId2);  // 返回相同资源

        // 数据库验证 - 只有一条记录
        assertEquals(1, orderRepo.countByRequestId(requestId));
      常见错误: "不测试重复提交，上线后出现重复订单/重复扣款"

    - 维度: "参数化批量测试"
      必要性: "推荐（参数 >= 3 个的接口）"
      示例: |
        // 使用 @ParameterizedTest 驱动多组输入
        @ParameterizedTest(name = "createOrder: {0} -> {1}")
        @CsvSource({
            "'',           400, MISSING_FIELD",     // userId 为空
            "'user1',      400, MISSING_FIELD",     // productId 缺失（需配合 JSON 构造）
            "'user1',      201, ''",                // 正常场景
        })
        void test_createOrder_parameterized(String userId, int expectedStatus, String expectedError) {
            String body = buildRequestBody(userId);
            ResultActions result = mockMvc.perform(post("/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content(body));

            result.andExpect(status().is(expectedStatus));
            if (!expectedError.isEmpty()) {
                result.andExpect(jsonPath("$.errorCode").value(expectedError));
            }
        }
      常见错误: "每个参数组合写一个独立测试方法，代码重复率高且维护困难"

# ============================================================
# 参考规范与模板
# ============================================================
参考规范与模板:
  - 资源名称: "测试思维框架"
    类型: "思维框架"
    说明: "应用契约建模、1+N+M模式、对抗性测试等原则。"

# ============================================================
# 备注与最佳实践
# ============================================================
备注与最佳实践:
  - "【对抗性测试】 强制测试越权场景，使用用户 A 的 Token 操作用户 B 的资源。"
  - "【变异思维】 通过逻辑反转验证接口健壮性。"
  - "【产出格式】 输出格式应包含：用例ID、追溯源、请求数据、预期响应码、预期响应体。"
  - "【工具推荐】 使用 PICT 或 AllPairs 进行 Pairwise 组合设计。"
