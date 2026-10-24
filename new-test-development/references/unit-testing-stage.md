# ============================================================
# 用户指令
# ============================================================
用户指令:
    - "单元测试"
    - "写单测"

# ============================================================
# 指令名称
# ============================================================
指令名称: "单元测试"

# ============================================================
# 任务描述
# ============================================================
任务描述: "遵循《测试思维框架》中的状态建模与三验证模型，针对具体的类（Class）或方法（Method）生成高覆盖率、依赖隔离的白盒测试代码。"

# ============================================================
# 前置条件_信息收集与澄清
# ============================================================
前置条件_信息收集与澄清:
  - 动作: "引用"
    内容: "被测源代码文件"
    参数: "$源代码"
    必要性: "必须"
  - 动作: "引用"
    内容: "核心类文档"
    参数: "$核心类文档"
    必要性: "可选"

# ============================================================
# 任务内容
# ============================================================
任务内容: |
  请扮演资深测试开发工程师 (SET)，基于提供的 `${源代码}` 和 `${核心类文档}`，并结合项目现有测试代码基线，严格遵循《测试思维框架》进行新增功能的单元测试设计与编码。

  ## Step 1: 核心逻辑列表提取

  **目标**: 从源代码或核心类文档中提取本次新增功能涉及的核心业务逻辑。

  **执行动作**:
  - 识别承载新增业务逻辑的类和方法（优先测试高风险类：金额计算、状态机、权限判断）
  - 提取每个方法的职责边界和业务规则
  - 识别方法的依赖关系（需要 Mock 的外部依赖）
  - 识别状态转换逻辑（状态机类）
  - 检查现有测试目录中是否已有相邻测试类、公共 fixture、builder 或 mock 封装可复用
  - 标记测试优先级（Critical/Major/Minor）

  ---

  ## Step 2: 测试清单生成

  **目标**: 基于《测试思维框架》，应用完整的思维链路为每个核心方法生成测试清单。

  **执行动作**:
  - 引用《测试思维框架》，应用其中的完整思维链路和方法论
  - 为每个核心方法系统性生成测试用例

  **产出**: 生成初版单元测试清单.md

  ---

  ## Step 3: 基于核心类文档 Review 与补全

  **目标**: 对照源代码、核心类文档和现有测试基线，自动审查测试清单的完备性。

  **执行动作**:
  1. **完整性检查**: 每个核心业务方法是否都生成了测试清单？
  2. **场景覆盖检查**:
     - 是否覆盖正常路径 + 异常路径？
     - 三验证维度（状态/交互/返回值）是否都有断言？
     - 状态机类是否穷举了所有转换路径（含非法转换）？
     - 涉及资产的逻辑是否验证了数据守恒？
     - 外部依赖是否已 Mock？Mock 失败场景是否测试？
     - 是否验证了副作用隔离？
     - 新增能力与现有流程的必要衔接点是否已有覆盖？
  3. **自动补全**: 发现缺失时，自动补充测试用例，更新清单。
  4. **迭代验证**: 重复检查-补全，直至完整覆盖。

  **产出**: 完善后的单元测试清单.md

  ---

  ## Step 4: AI 专业自审（必须执行，不可跳过）

  **目标**: 从资深测试工程师视角对初版清单做独立审查，发现遗漏并补全。

  **执行动作**:
  1. **方法覆盖检查**：逐一比对被测类的 public 方法与清单，确认每个方法都有对应用例。
  2. **三验证维度检查**：每个用例是否都明确了要验证的维度（返回值 / 状态变更 / 依赖交互），不允许"仅验证不抛异常"这类弱断言。
  3. **边界值检查**：数值参数是否覆盖 0、负数、边界值、超边界？字符串是否覆盖空串、空格、超长？
  4. **依赖隔离检查**：是否所有外部依赖（DB/RPC/File）都明确了 Mock 策略？
  5. **测试独立性检查**：是否存在测试间共享可变状态？
  6. **补全**：发现遗漏自动补充，并标注 `[AI补全]` 便于人工复核。

  **产出规范**:
  - **产出文件**: `test_case/单元测试清单.md`（含 `[AI补全]` 标注项）
  - **产出位置**: `test_case/` 目录

  > **⏸ PAUSE — 输出清单摘要，等待人工确认后再进入下一步。**
  > 摘要格式：总用例数 / 覆盖方法数 / AI补全项数 / 待人工决策项

# ============================================================
# Good/Bad 单元测试对比
# ============================================================
Good_Bad_对比:
  示例1_测试命名:
    Bad: |
      @Test
      void test1() { ... }
      @Test
      void testOrder() { ... }
    Good: |
      @Test
      void test_cancel_whenPending_shouldChangeStatusToCanceled() { ... }
      @Test
      void test_cancel_whenAlreadyCanceled_shouldThrowException() { ... }
    说明: "命名必须描述 Method + Condition + ExpectedResult"

  示例2_断言完整性:
    Bad: |
      @Test
      void test_createOrder() {
          orderService.create(request);
          // 没有断言！测试永远通过
      }
    Good: |
      @Test
      void test_create_whenValid_shouldPersistAndReturnId() {
          // Given
          CreateOrderRequest request = buildValidRequest();
          // When
          OrderId result = orderService.create(request);
          // Then - 三验证模型
          assertNotNull(result);                              // 返回值验证
          verify(orderRepo, times(1)).save(any(Order.class)); // 依赖交互验证
          Order saved = captorOrder.getValue();
          assertEquals(OrderStatus.PENDING, saved.getStatus()); // 状态变更验证
      }
    说明: "每个测试必须包含至少一个有效断言，推荐覆盖三验证模型"

  示例3_依赖隔离:
    Bad: |
      @SpringBootTest  // 启动整个 Spring Context，慢！
      class OrderServiceTest {
          @Autowired
          private OrderService orderService;
      }
    Good: |
      @ExtendWith(MockitoExtension.class)  // 纯 Mockito，毫秒级
      class OrderServiceTest {
          @Mock private OrderRepository orderRepo;
          @Mock private InventoryService inventoryService;
          @InjectMocks private OrderService orderService;
      }
    说明: "单元测试严禁启动 Spring Context，使用 Mockito 隔离所有外部依赖"

  示例4_巨型测试方法:
    Bad: |
      @Test
      void test_orderLifecycle() {
          // 创建订单
          Order order = orderService.create(request);
          assertNotNull(order);
          assertEquals(OrderStatus.PENDING, order.getStatus());
          // 支付订单
          orderService.pay(order.getId());
          assertEquals(OrderStatus.PAID, order.getStatus());
          // 发货
          orderService.ship(order.getId());
          assertEquals(OrderStatus.SHIPPED, order.getStatus());
          // 签收
          orderService.confirm(order.getId());
          assertEquals(OrderStatus.COMPLETED, order.getStatus());
          // ... 还有 20 行断言
      }
    Good: |
      @Test
      void test_create_whenValid_shouldReturnPendingOrder() { ... }
      @Test
      void test_pay_whenPending_shouldChangeStatusToPaid() { ... }
      @Test
      void test_ship_whenPaid_shouldChangeStatusToShipped() { ... }
      @Test
      void test_confirm_whenShipped_shouldChangeStatusToCompleted() { ... }
    说明: "单个测试方法只验证一个行为。方法名包含'and'或断言超过10行时必须拆分"

  示例5_窥探私有实现:
    Bad: |
      @Test
      void test_calculateDiscount() {
          // 通过反射访问私有方法
          Method method = OrderService.class.getDeclaredMethod("calculateInternalDiscount", BigDecimal.class);
          method.setAccessible(true);
          BigDecimal result = (BigDecimal) method.invoke(orderService, new BigDecimal("100"));
          assertEquals(new BigDecimal("10"), result);
      }
    Good: |
      @Test
      void test_create_whenHasDiscount_shouldApplyDiscountToTotal() {
          // 通过公共接口间接验证折扣逻辑
          CreateOrderRequest request = buildRequest(amount: 100, discountCode: "10OFF");
          Order order = orderService.create(request);
          assertEquals(new BigDecimal("90"), order.getTotalAmount());
      }
    说明: "永远通过公共接口测试。私有方法是实现细节，通过公共方法间接验证"

  示例6_测试间数据残留:
    Bad: |
      private static Order sharedOrder; // 类级别共享可变状态
      @Test void test1_create() { sharedOrder = orderService.create(...); }
      @Test void test2_cancel() { orderService.cancel(sharedOrder.getId()); } // 依赖 test1
    Good: |
      @Test
      void test_cancel_whenPending_shouldSuccess() {
          Order order = createTestOrder(OrderStatus.PENDING); // 每个测试自己准备数据
          orderService.cancel(order.getId());
          assertEquals(OrderStatus.CANCELED, order.getStatus());
      }
    说明: "每个测试方法独立准备数据。使用 @BeforeEach 重置状态，不依赖执行顺序"

# ============================================================
# AAA 断言模式表
# ============================================================
AAA断言模式表:
  说明: "Arrange-Act-Assert 是单元测试的标准结构，对应 Given-When-Then"
  模式:
    - 阶段: "Arrange (Given)"
      职责: "准备测试数据和 Mock 配置"
      要求: "每个测试独立准备数据，不依赖共享可变状态"
      示例: |
        Order order = new Order("id", OrderStatus.PENDING);
        when(repo.findById("id")).thenReturn(Optional.of(order));

    - 阶段: "Act (When)"
      职责: "执行被测方法"
      要求: "只调用一次被测方法，不混入断言逻辑"
      示例: |
        OrderResult result = orderService.cancel("id");

    - 阶段: "Assert (Then)"
      职责: "验证执行结果"
      要求: "从状态变更、依赖交互、返回值三个维度断言"
      断言类型表:
        - 类型: "返回值断言"
          方法: "assertEquals / assertNotNull / assertThrows"
          适用: "方法有返回值或应抛异常"
        - 类型: "状态变更断言"
          方法: "assertEquals(expected, obj.getField())"
          适用: "方法修改了对象内部状态"
        - 类型: "依赖交互断言"
          方法: "verify(mock, times(N)).method(args)"
          适用: "方法应调用外部依赖"
        - 类型: "副作用隔离断言"
          方法: "assertEquals(originalValue, shadowObj.getField())"
          适用: "验证无关对象未被修改"
        - 类型: "异常断言"
          方法: "assertThrows(ExType.class, () -> method())"
          适用: "方法应在特定条件下抛异常"
        - 类型: "数据守恒断言"
          方法: "assertEquals(totalBefore, totalAfter)"
          适用: "涉及资产流转的业务逻辑"

# ============================================================
# 参考规范与模板
# ============================================================
参考规范与模板:
  - 资源名称: "测试思维框架"
    类型: "思维框架"
    说明: "应用状态建模、三验证模型、静态契约验证等原则。"

# ============================================================
# 备注与最佳实践
# ============================================================
备注与最佳实践:
  - "【领域原语】 若使用了 Money 等类型，无需在测试中重复校验格式。"
  - "【副作用验证】 建议增加'影子对象'断言，验证无关对象未被修改。"
  - "【独立性】 确保每个测试用例互不依赖，可独立运行。"
  - "【命名规范】 测试方法命名格式：`test_[Method]_[Condition]_[ExpectedResult]`"
  - "【技术栈】 使用 JUnit 5 + Mockito 进行单元测试开发。"
