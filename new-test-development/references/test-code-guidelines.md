文档名称: "测试代码规范"
文档描述: "定义项目的测试代码研发规范，包括目录结构、命名规则、编码标准及覆盖率要求。"

文档内容: |
  # 测试代码规范

  本文档旨在定义项目的测试代码研发规范，确保测试代码的可维护性、一致性和有效性。

  ---

  ## 0. 测试目录与文件命名规范（强制）

  ### 0.1 目录命名——统一使用英文，所有语言一致

  ```
  tests/
  ├── unit/          # 单元测试（不可用中文目录名）
  ├── api/           # 接口测试
  └── functional/    # 功能测试
  ```

  > 禁止使用中文目录名（如"单元测试/"），统一使用 `unit/`、`api/`、`functional/`。
  > 目录下必须有 `__init__.py`（Python）或 `package-info.java`（Java）以确保测试发现。

  ### 0.2 文件命名——遵循对应语言约定，只给规范不强制风格

  | 层级 | Python | Java / Kotlin | Go | 命名语义 |
  |------|--------|---------------|----|---------|
  | 单元测试 | `test_{ClassName}.py` | `{ClassName}Test.java` | `{class_name}_test.go` | 被测类名 |
  | 接口测试 | `test_{EndpointName}.py` | `{EndpointName}IT.java` | `{endpoint}_api_test.go` | 接口/端点名 |
  | 功能测试 | `test_{FeatureName}.py` | `{FeatureName}FlowTest.java` | `{feature}_flow_test.go` | 业务特性名 |

  **示例（Python）**：
  ```
  tests/unit/test_TaskHandler.py      # 被测类：TaskHandler
  tests/unit/test_ResultHandler.py    # 被测类：ResultHandler
  tests/api/test_Execute.py           # 被测接口：POST /execute
  tests/api/test_Query.py             # 被测接口：GET /query
  tests/functional/test_SubmitQuery.py  # 被测特性：提交查询流程
  ```

  **示例（Java）**：
  ```
  src/test/java/.../unit/TaskHandlerTest.java
  src/test/java/.../api/ExecuteIT.java
  src/test/java/.../functional/SubmitQueryFlowTest.java
  ```

  ### 0.3 测试清单文件命名（test_case/ 目录）

  | 清单 | 文件名 |
  |------|--------|
  | 单元测试清单 | `test_case/单元测试清单.md` |
  | 接口测试清单 | `test_case/接口测试清单.md` |
  | 功能测试清单 | `test_case/功能测试清单.md` |
  | 测试报告 | `test_case/测试报告.md` |

  ---

  ## 1. 测试工程目录
  
  测试代码应与业务代码保持严格的对应关系，目录结构遵循 Maven/Gradle 标准。
  
  ### 1.1 标准目录结构
  
  ```text
  src/test/java/com/example/{project_name}/
  ├── {module}/                       # 对应业务模块
  │   ├── service/                    # 单元测试 (Unit Test)
  │   │   └── OrderServiceTest.java
  │   ├── core/                       # 核心能力测试
  │       └── GenIdHandlerTest.java

  │
  ├── component/                      # 组件/工具测试
  │   ├── util/
  │   └── adapter/
  │
  ├── integration/                    # 接口测试 (API Test)
  │   ├── api/                        # API Client 层
  │   │   └── UserApiClient.java
  │   ├── cases/                      # 业务场景层
  │   │   └── UserRegisterTest.java
  │   └── base/                       # 测试基类
  │       └── BaseApiTest.java
  │
  └── functional/                     # 功能测试 (Functional Test / E2E)
      ├── flows/                      # 业务流程测试
      │   └── OrderCancelFlowTest.java
      ├── features/                   # BDD Feature 文件 (Cucumber)
      │   └── order_cancel.feature
      └── base/                       # 功能测试基类
          └── BaseFunctionalTest.java
  ```
  
  ### 1.2 资源目录
  
  ```text
  src/test/resources/
  ├── application-test.yml            # 测试环境配置
  ├── mock/                           # Mock 数据文件 (JSON/XML)
  │   └── user_data.json
  └── sql/                            # 内存数据库初始化脚本
      ├── schema.sql
      └── data.sql
  ```
  
  ---
  
  ## 2. 命名规范
  
  测试类的命名应具有明确的语义，便于快速定位和理解测试目标。
  
  ### 2.1 类命名
  
  | 类型 | 规范格式 | 示例 |
  | :--- | :--- | :--- |
  | **单元测试类** | `{TargetClass}Test` | `OrderServiceTest` |
  | **接口测试类** | `{Scenario}IT` (IT = API Test) | `OrderApiIT` |
  
  **命名原则**：使用 `IT` 后缀遵循 Maven/Gradle 约定，便于在 CI/CD 中分离执行快速测试（`*Test.java`）和慢速测试（`*IT.java`）。
  | **功能测试类** | `{Flow}FlowTest` 或 `{Feature}FeatureTest` | `OrderCancelFlowTest` |
  | **基类** | `Base{Type}Test` | `BaseServiceTest` |
  | **工具类** | `Test{UtilName}` | `TestDataFactory` |
  
  ### 2.2 方法命名
  
  遵循 `test_{Method}_{Condition}_{Result}` 格式，强调 **G-W-T (Given-When-Then)** 语义。
  
  *   **Method**: 被测方法名
  *   **Condition**: 测试条件/场景
  *   **Result**: 预期结果
  
  **示例**:
  *   `test_createOrder_WhenStockInsufficient_ShouldThrowException()`
  *   `test_getUser_WithValidId_ShouldReturnUser()`
  
  ### 2.3 三种测试类型对比表
  
  | 维度 | 单元测试 | 接口测试 | 功能测试 |
  | :--- | :--- | :--- | :--- |
  | **测试对象** | 单个类/方法 | 单个 API 接口 | 完整业务流程 |
  | **执行速度** | 极快（毫秒级） | 快（秒级） | 慢（分钟级） |
  | **依赖处理** | Mock 所有外部依赖 | 真实数据库，Mock 外部服务 | 真实环境或接近真实 |
  | **测试目标** | 验证业务逻辑正确性 | 验证接口契约正确性 | 验证业务闭环 |
  | **典型场景** | `Order.cancel()` 方法 | `POST /orders` 接口 | 创建订单 → 支付 → 发货 |
  | **技术栈** | JUnit 5 + Mockito | Spring Boot Test + MockMvc | Spring Boot Test + Testcontainers |
  | **何时使用** | 每次代码提交 | 每次构建 | 每次发布前 |
  | **覆盖率要求** | 核心业务 ≥ 80% | 所有接口 100% | 核心流程 100% |
  | **执行频率** | 最高（每次提交） | 中（每次构建） | 低（每次发布） |
  
  ### 2.4 何时使用哪种测试（决策树）
  
  ```
  开始
   │
   ├─ 测试单个类的方法逻辑？
   │  └─ 是 → 【单元测试】
   │     • 使用 Mock 隔离所有依赖
   │     • 验证状态变更、依赖交互、返回值
   │
   ├─ 测试单个 API 接口的契约？
   │  └─ 是 → 【接口测试】
   │     • 使用真实数据库
   │     • 验证 1+N+M 场景（成功+参数异常+业务异常）
   │
   └─ 测试完整的业务流程？
      └─ 是 → 【功能测试】
         • 串联多个接口
         • 验证端到端数据流转和状态变迁
  ```
  
  **具体场景示例**：
  
  | 场景 | 测试类型 | 原因 |
  | :--- | :--- | :--- |
  | 测试 `Order.cancel()` 方法的业务逻辑 | 单元测试 | 聚焦单个方法，快速验证 |
  | 测试 `POST /orders` 接口的参数校验 | 接口测试 | 验证 HTTP 契约，需要真实数据库 |
  | 测试"用户下单 → 支付 → 发货"完整流程 | 功能测试 | 跨多个接口，验证业务闭环 |
  | 测试金额计算的精度问题 | 单元测试 | 纯逻辑计算，无需外部依赖 |
  | 测试接口的 SQL 注入防护 | 接口测试 | 需要真实数据库验证安全机制 |
  | 测试支付失败后的订单回滚流程 | 功能测试 | 涉及多个服务和状态流转 |
  
  ---
  
  ## 3. 单元测试规范 (Unit Test)
  
  **原则**: 快速、独立、可重复。
  
  **核心设计原则**：
  - **三验证模型**：必须从状态变更、依赖交互、返回值三个维度进行断言，确保测试完整性。
  - **依赖隔离**：所有外部依赖必须 Mock，严禁连接真实数据库、Redis 或发起 HTTP 请求。
  - **无 Spring Context**：严禁启动 Spring Context（除非测试配置类本身），保持测试快速执行。
  
  ### 3.1 技术栈
  *   **框架**: JUnit 5
  *   **Mock**: Mockito (严禁在单元测试中启动 Spring Context，除非测试配置类)
  *   **断言**: AssertJ (推荐) 或 JUnit Assertions
  
  ### 3.2 编码标准
  
  1.  **依赖隔离**: 使用 `@Mock` 模拟所有外部依赖 (Repository, RPC Client, Redis)，使用 `@InjectMocks` 注入被测对象。
  2.  **严禁外连**: 单元测试**绝对不允许**连接真实的数据库、Redis 或发起 HTTP 请求。
  3.  **三段式结构**: 代码块必须清晰划分为 `Given` (准备), `When` (执行), `Then` (断言)。
  4.  **三验证模型**: 从**状态变更**、**依赖交互**、**返回值**三个维度进行断言。
  5.  **副作用隔离**: 验证"变了什么"，也要验证"没变什么"（影子对象验证）。
  6.  **静态契约验证 (Domain Primitive)**: 推广领域原语，利用类型系统（如 `Money`, `Email`）在构造时拦截非法值，减少运行时测试。
  7.  **白盒运行时断言**: 在被测逻辑中间步骤植入断言，实时监控守恒律。
  8.  **差分测试**: 对高风险算法实施异构代码比对（双盲验证）。
  
  ```java
  @ExtendWith(MockitoExtension.class)
  class UserServiceTest {
      @Mock
      private UserRepo userRepo;
      @InjectMocks
      private UserService userService;
  
      @Test
      void test_register_WhenUserExists_ShouldFail() {
          // Given
          when(userRepo.exists("tom")).thenReturn(true);
          // When
          boolean result = userService.register("tom");
          // Then
          assertFalse(result);
      }
  }
  ```
  
  ### 3.3 实践示例：订单取消逻辑
  
  ```java
  @ExtendWith(MockitoExtension.class)
  class OrderTest {
      @Mock
      private OrderRepository mockRepo;
      @Mock
      private InventoryService mockInventory;
      @InjectMocks
      private Order order;
  
      @Test
      void test_cancel_whenPending_shouldSuccess() {
          // Given
          Order order = new Order("order1", OrderStatus.PENDING);
          order.setRepository(mockRepo);
          order.setInventoryService(mockInventory);
          
          // When
          order.cancel();
          
          // Then - 三验证模型：状态变更、依赖交互、返回值
          assertEquals(OrderStatus.CANCELED, order.getStatus());  // 1. 状态变更验证
          verify(mockRepo, times(1)).save(order);                  // 2. 依赖交互验证
          verify(mockInventory, times(1)).restore(order.getProductId(), order.getQuantity());  // 2. 依赖交互验证
          // 3. 返回值验证：无返回值方法，通过状态和交互验证即可
      }
  
      @Test
      void test_cancel_shouldNotAffectOtherOrders() {
          // Given - 创建目标对象和影子对象
          Order targetOrder = new Order("order1", OrderStatus.PENDING);
          Order shadowOrder = new Order("order2", OrderStatus.PENDING);
          
          // When
          targetOrder.cancel();
          
          // Then - 副作用隔离验证
          assertEquals(OrderStatus.CANCELED, targetOrder.getStatus());
          assertEquals(OrderStatus.PENDING, shadowOrder.getStatus()); // 影子对象不变
      }
      
      /**
       * 静态契约验证 (Domain Primitive) 示例
       * 通过构造函数拦截非法值，测试代码中无需再写异常分支测试
       */
      @Test
      void test_domainPrimitive_usage() {
          // Money 构造函数内部已包含校验：if (value < 0) throw ...
          Money amount = new Money(new BigDecimal("100"));
          assertNotNull(amount);
      }
      
      /**
       * 白盒运行时断言 & 数据守恒 示例
       * 验证业务逻辑执行前后的守恒律
       */
      @Test
      void test_transfer_shouldConserveTotal() {
          Account from = new Account(new Money(100));
          Account to = new Account(new Money(50));
          Money totalBefore = from.balance().add(to.balance());
          
          // 执行转账逻辑
          transferService.transfer(from, to, new Money(30));
          
          Money totalAfter = from.balance().add(to.balance());
          assertEquals(totalBefore, totalAfter); // 总额守恒
      }
      
      /**
       * 差分测试 示例
       * 对比两个异构实现的输出是否一致
       */
      @Test
      void test_differential_calculation() {
          BigDecimal input = new BigDecimal("1234.56");
          // 被测实现
          BigDecimal result1 = complexCalculator.calculate(input);
          // 参考实现（或简化实现）
          BigDecimal result2 = referenceCalculator.calculate(input);
          
          assertEquals(result1, result2);
      }
  }
  ```
  
  ---
  
  ## 4. 接口测试规范 (API Test)
  
  **定位**: 测试 HTTP API 接口与数据库、缓存等组件的集成，验证接口契约的正确性。
  
  **原则**: 真实、完整、覆盖契约。
  
  ### 4.1 技术栈
  *   **框架**: Spring Boot Test (启动部分或全部 Context)
  *   **HTTP客户端**: Rest-Assured
  *   **数据库**: H2 (内存数据库) 或 Testcontainers (推荐)
  
  **核心设计原则**：
  - **真实数据库**：必须使用真实数据库（H2 或 Testcontainers），用于验证 SQL 正确性、事务行为、数据库约束和 ORM 映射。
  - **数据隔离**：每个测试方法执行后必须回滚数据，保证用例独立性。
  - **1+N+M 模式**：覆盖契约成功、参数异常、业务与安全异常三类场景。
  
  ### 4.2 编码标准
  
  1.  **分层架构**: 遵循 `Client` (封装请求) -> `Case` (业务场景) -> `Data` (数据驱动) 的三层架构。
  2.  **环境隔离**: 使用 `application-test.yml` 隔离配置，避免污染开发/生产环境。
  3.  **数据回滚**: 每个测试方法执行后，必须回滚数据库状态 (使用 `@Transactional` 或手动清理)，保证用例独立性。
  4.  **1+N+M 模式**: 覆盖契约成功 (1)、参数异常 (N)、业务与安全异常 (M) 三类场景。
  5.  **对抗性测试**: 强制测试 SQL 注入、XSS 注入、水平/垂直越权场景。
  6.  **幂等验证**: 对于创建、更新类接口，使用相同 request-id 重复调用验证。
  
  ```java
  @SpringBootTest(webEnvironment = RANDOM_PORT)
  @AutoConfigureMockMvc
  @Transactional  // 数据隔离：每个测试方法执行后自动回滚
  @Rollback
  class OrderApiIT {
      @Autowired
      private MockMvc mockMvc;
      
      @Autowired
      private OrderRepository orderRepo;  // 使用真实数据库，验证 SQL 和事务
      
      @Test
      void test_createOrder_WhenValidRequest_ShouldReturn201() {
          // Given - "1" 契约成功场景
          String requestBody = """
              {
                "userId": "user123",
                "productId": "prod456",
                "quantity": 2,
                "couponCode": "COUPON001"
              }
              """;
          
          // When & Then
          mockMvc.perform(post("/orders")
                  .contentType(MediaType.APPLICATION_JSON)
                  .content(requestBody))
              .andExpect(status().isCreated())
              .andExpect(jsonPath("$.orderId").exists());
          
          // 验证数据库中的记录（真实数据库验证）
          Order savedOrder = orderRepo.findByOrderId(...);
          assertNotNull(savedOrder);
          assertEquals("user123", savedOrder.getUserId());
      }
      
      @Test
      void test_createOrder_WhenUserIdMissing_ShouldReturn400() {
          // Given - "N" 参数异常场景
          String requestBody = """
              {
                "productId": "prod456",
                "quantity": 2
              }
              """;
          
          // When & Then
          mockMvc.perform(post("/orders")
                  .contentType(MediaType.APPLICATION_JSON)
                  .content(requestBody))
              .andExpect(status().isBadRequest())
              .andExpect(jsonPath("$.errorCode").value("MISSING_FIELD"));
      }
      
      @Test
      void test_createOrder_WhenStockInsufficient_ShouldReturn400() {
          // Given - "M" 业务异常场景
          String requestBody = """
              {
                "userId": "user123",
                "productId": "out_of_stock_product",
                "quantity": 100
              }
              """;
          
          // When & Then
          mockMvc.perform(post("/orders")
                  .contentType(MediaType.APPLICATION_JSON)
                  .content(requestBody))
              .andExpect(status().isBadRequest())
              .andExpect(jsonPath("$.errorCode").value("OUT_OF_STOCK"));
      }
      
      @Test
      void test_createOrder_WhenSqlInjection_ShouldBeBlocked() {
          // Given - "M" 安全对抗场景
          String requestBody = """
              {
                "userId": "' OR '1'='1",
                "productId": "prod456",
                "quantity": 1
              }
              """;
          
          // When & Then - 应被安全拦截，不暴露错误详情
          mockMvc.perform(post("/orders")
                  .contentType(MediaType.APPLICATION_JSON)
                  .content(requestBody))
              .andExpect(status().isBadRequest());
      }
  }
  ```
  
  ---
  
  ## 5. 功能测试规范 (Functional Test / E2E Test)
  
  **定位**: 功能测试是端到端的业务流程测试，验证完整的用户故事和业务闭环，通常涉及多个接口的串联调用。
  
  **与接口测试的区别**:
  - **接口测试**: 聚焦单个 API 接口的契约验证（输入/输出、参数校验、业务规则）
  - **功能测试**: 聚焦完整的业务流程（如：创建订单 → 支付 → 发货），验证跨接口的数据流转和状态变迁
  
  **原则**: 端到端、业务闭环、数据守恒。
  
  ### 5.1 技术栈
  *   **框架**: Spring Boot Test (全量 Context) 或 Cucumber (BDD)
  *   **HTTP客户端**: Rest-Assured 或 MockMvc
  *   **数据库**: Testcontainers (推荐) 或真实测试环境
  *   **消息队列**: Testcontainers Kafka/RabbitMQ (如需要)
  
  **核心设计原则**：
  - **Testcontainers 优先**：使用容器化测试环境，确保环境一致性、隔离性和可重复性。
  - **端到端验证**：验证跨接口的数据流转和状态变迁，而非单个接口的重复测试。
  - **四维破坏法**：从输入数据、业务流程/状态、权限、外部依赖四个维度推导异常场景。
  
  ### 5.2 编码标准
  
  1.  **BDD 结构**: 严格遵循 `Given-When-Then` 结构，每个测试用例对应一个用户故事。
  2.  **四维破坏法**: 从输入数据 (A)、业务流程/状态 (B)、权限 (C)、外部依赖 (D) 四个维度推导异常场景。
  3.  **数据守恒验证**: 涉及资产流转的功能，必须验证 `Sum(所有账户余额) == 初始总额`。
  4.  **副作用隔离**: 验证全流程结束后，无关用户的账户数据未受 Mutation。
  5.  **故障韧性**: 强制模拟第三方服务超时、失败等外部依赖故障。
  
  ### 5.3 实践示例：订单取消功能测试
  
  ```java
  @SpringBootTest(webEnvironment = RANDOM_PORT)
  @AutoConfigureMockMvc
  @Testcontainers  // 使用 Testcontainers 确保环境一致性和隔离性
  class OrderCancelFlowTest {
      @Container
      static MySQLContainer<?> mysql = new MySQLContainer<>("mysql:8.0")
              .withDatabaseName("testdb")
              .withUsername("test")
              .withPassword("test");
      
      @Autowired
      private MockMvc mockMvc;
      
      @Autowired
      private OrderRepository orderRepo;
      
      @Autowired
      private InventoryRepository inventoryRepo;
      
      @Test
      @Transactional
      @Rollback
      void test_cancelOrder_WhenPending_ShouldSuccess() {
          // Given - 主成功路径
          Order order = createOrder(OrderStatus.PENDING);
          int initialStock = inventoryRepo.findByProductId(order.getProductId()).getQuantity();
          
          // When
          mockMvc.perform(post("/orders/{orderId}/cancel", order.getId())
                  .header("Authorization", "Bearer " + getToken(order.getUserId())))
              .andExpect(status().isOk());
          
          // Then - 状态流转验证
          Order canceledOrder = orderRepo.findById(order.getId()).orElseThrow();
          assertEquals(OrderStatus.CANCELED, canceledOrder.getStatus());
          
          // Then - 数据守恒验证（库存恢复）
          int finalStock = inventoryRepo.findByProductId(order.getProductId()).getQuantity();
          assertEquals(initialStock + order.getQuantity(), finalStock);
      }
      
      @Test
      @Transactional
      @Rollback
      void test_cancelOrder_WhenPaid_ShouldFail() {
          // Given - 维度B：业务流程/状态异常
          Order order = createOrder(OrderStatus.PAID);
          
          // When & Then
          mockMvc.perform(post("/orders/{orderId}/cancel", order.getId())
                  .header("Authorization", "Bearer " + getToken(order.getUserId())))
              .andExpect(status().isBadRequest())
              .andExpect(jsonPath("$.errorCode").value("ORDER_ALREADY_PAID"));
      }
      
      @Test
      @Transactional
      @Rollback
      void test_cancelOrder_WhenUserA_CancelUserBOrder_ShouldFail() {
          // Given - 维度C：权限异常（水平越权）
          Order orderB = createOrder(OrderStatus.PENDING, "userB");
          String tokenA = getToken("userA");
          
          // When & Then
          mockMvc.perform(post("/orders/{orderId}/cancel", orderB.getId())
                  .header("Authorization", "Bearer " + tokenA))
              .andExpect(status().isForbidden());
      }
      
      @Test
      @Transactional
      @Rollback
      void test_cancelOrder_WhenInventoryServiceTimeout_ShouldCompensate() {
          // Given - 维度D：外部依赖故障
          Order order = createOrder(OrderStatus.PENDING);
          // 模拟库存服务超时（通过 WireMock 或 Testcontainers）
          mockInventoryServiceTimeout();
          
          // When
          mockMvc.perform(post("/orders/{orderId}/cancel", order.getId())
                  .header("Authorization", "Bearer " + getToken(order.getUserId())))
              .andExpect(status().isOk());
          
          // Then - 故障韧性验证：订单应取消成功，库存恢复通过异步补偿完成
          Order canceledOrder = orderRepo.findById(order.getId()).orElseThrow();
          assertEquals(OrderStatus.CANCELED, canceledOrder.getStatus());
          // 验证补偿任务已创建
          assertTrue(compensationTaskExists(order.getId()));
      }
      
      @Test
      @Transactional
      @Rollback
      void test_cancelOrder_ShouldNotAffectOtherOrders() {
          // Given - 副作用隔离验证
          Order orderA = createOrder(OrderStatus.PENDING, "userA");
          Order orderB = createOrder(OrderStatus.PENDING, "userB");
          OrderStatus orderBStatusBefore = orderB.getStatus();
          
          // When
          mockMvc.perform(post("/orders/{orderId}/cancel", orderA.getId())
                  .header("Authorization", "Bearer " + getToken("userA")))
              .andExpect(status().isOk());
          
          // Then - 验证影子对象（订单B）未被影响
          Order orderBAfter = orderRepo.findById(orderB.getId()).orElseThrow();
          assertEquals(orderBStatusBefore, orderBAfter.getStatus());
      }
      
      private Order createOrder(OrderStatus status) {
          return createOrder(status, "defaultUser");
      }
      
      private Order createOrder(OrderStatus status, String userId) {
          // 创建测试订单的辅助方法
          // ...
      }
  }
  ```
  
  ### 5.4 BDD 风格示例 (Cucumber)
  
  若使用 Cucumber 进行 BDD 测试，功能测试用例应编写为 `.feature` 文件：
  
  ```gherkin
  Feature: 订单取消功能
    As a 买家
    I want to 取消待支付的订单
    So that 我可以放弃购买
  
    Scenario: 成功取消待支付订单
      Given 我有一个状态为"待支付"的订单
      When 我点击取消订单
      Then 订单状态应变为"已取消"
      And 库存应恢复
  
    Scenario: 无法取消已支付订单
      Given 我有一个状态为"已支付"的订单
      When 我点击取消订单
      Then 系统应提示"订单已支付，无法取消"
  
    Scenario: 用户A无法取消用户B的订单
      Given 用户B有一个待支付的订单
      When 用户A尝试取消该订单
      Then 系统应提示"无权限操作"
  ```
  
  ---
  
  ---
  
  ## 6. 反模式与陷阱（避免这些常见错误）
  
  ### 6.1 单元测试反模式
  
  #### ❌ 反模式 1: 在单元测试中启动 Spring Context
  
  ```java
  // ❌ 错误：启动 Spring Context 会让测试变慢
  @SpringBootTest
  class OrderServiceTest {
      @Autowired
      private OrderService orderService;
  }
  
  // ✅ 正确：使用 Mockito，不启动 Spring
  @ExtendWith(MockitoExtension.class)
  class OrderServiceTest {
      @Mock
      private OrderRepository repo;
      @InjectMocks
      private OrderService orderService;
  }
  ```
  
  #### ❌ 反模式 2: 测试方法之间有依赖
  
  ```java
  // ❌ 错误：test2 依赖 test1 的执行结果
  @Test
  void test1_createOrder() {
      order = orderService.create(...);
  }
  
  @Test
  void test2_cancelOrder() {
      orderService.cancel(order.getId()); // order 可能为 null
  }
  
  // ✅ 正确：每个测试方法独立
  @Test
  void test_cancelOrder() {
      Order order = createTestOrder(); // 自己创建测试数据
      orderService.cancel(order.getId());
  }
  ```
  
  #### ❌ 反模式 3: 测试逻辑过于复杂
  
  ```java
  // ❌ 错误：测试代码本身有复杂的 if/else
  @Test
  void test_complex() {
      if (condition1) {
          // 大量逻辑
      } else if (condition2) {
          // 更多逻辑
      }
  }
  
  // ✅ 正确：测试代码应该简单直接
  @Test
  void test_whenCondition1_shouldReturnX() {
      // 只测试 condition1 的情况
  }
  ```
  
  ### 6.2 接口测试反模式
  
  #### ❌ 反模式 4: 测试数据污染
  
  ```java
  // ❌ 错误：测试数据没有清理，影响后续测试
  @Test
  void test_createUser() {
      mockMvc.perform(post("/users").content(...));
      // 没有清理，数据库中残留测试数据
  }
  
  // ✅ 正确：使用 @Transactional + @Rollback
  @Test
  @Transactional
  @Rollback
  void test_createUser() {
      mockMvc.perform(post("/users").content(...));
      // 自动回滚，数据自动清理
  }
  ```
  
  #### ❌ 反模式 5: 只测试 Happy Path
  
  ```java
  // ❌ 错误：只测试成功场景
  @Test
  void test_createOrder() {
      // 只测试合法请求
  }
  
  // ✅ 正确：覆盖 1+N+M 场景
  @Test
  void test_createOrder_WhenValid_ShouldReturn201() { }  // 1
  @Test
  void test_createOrder_WhenUserIdMissing_ShouldReturn400() { }  // N
  @Test
  void test_createOrder_WhenStockInsufficient_ShouldReturn400() { }  // M
  ```
  
  ### 6.3 功能测试反模式
  
  #### ❌ 反模式 6: 功能测试变成接口测试的重复
  
  ```java
  // ❌ 错误：功能测试只是重复调用接口测试已经覆盖的接口
  @Test
  void test_orderFlow() {
      createOrder();  // 接口测试已经覆盖
      payOrder();     // 接口测试已经覆盖
      shipOrder();    // 接口测试已经覆盖
  }
  
  // ✅ 正确：功能测试应该验证跨接口的数据流转
  @Test
  void test_orderFlow() {
      String orderId = createOrder();
      payOrder(orderId);
      // 验证：订单状态从 PENDING → PAID
      // 验证：支付记录与订单关联
      // 验证：库存已扣减
      shipOrder(orderId);
      // 验证：订单状态从 PAID → SHIPPED
      // 验证：物流单号已关联
  }
  ```
  
  ---
  
  ## 7. 性能与扩展性
  
  ### 7.1 测试执行时间优化
  
  **单元测试优化**：
  - 使用 `@Mock` 而不是 `@MockBean`（避免启动 Spring Context）
  - 避免在 `@BeforeEach` 中执行耗时操作
  - 使用并行执行（JUnit 5 支持）
  
  **接口测试优化**：
  - 使用 H2 内存数据库而不是 MySQL（更快）
  - 使用 `@Sql` 批量初始化数据，而不是逐个插入
  - 使用 `@DirtiesContext` 最小化 Context 重启
  
  **功能测试优化**：
  - 使用 Testcontainers 的容器复用（`@Container(shared = true)`）
  - 将慢速测试标记为 `@Tag("slow")`，在 CI 中单独执行
  - 使用测试数据工厂模式，避免重复创建数据
  
  ### 7.2 并发测试策略
  
  **何时需要并发测试**：
  - 涉及分布式锁的场景（如：库存扣减）
  - 涉及状态机的并发转换（如：订单状态变更）
  - 涉及余额操作的场景（如：转账）
  
  **并发测试示例**：
  ```java
  @Test
  void test_concurrentInventoryDeduction() throws InterruptedException {
      int threadCount = 10;
      CountDownLatch latch = new CountDownLatch(threadCount);
      ExecutorService executor = Executors.newFixedThreadPool(threadCount);
      
      for (int i = 0; i < threadCount; i++) {
          executor.submit(() -> {
              try {
                  orderService.createOrder(productId, 1);
              } finally {
                  latch.countDown();
              }
          });
      }
      
      latch.await(5, TimeUnit.SECONDS);
      
      // 验证：库存扣减正确，没有超卖
      Product product = productRepo.findById(productId);
      assertEquals(expectedStock, product.getStock());
  }
  ```
  
  ### 7.3 大数据量测试
  
  **场景**：测试接口在处理大量数据时的性能
  
  **策略**：
  - 使用 `@ParameterizedTest` 测试不同数据量（100、1000、10000）
  - 使用性能断言（如：响应时间 < 1秒）
  - 标记为 `@Tag("performance")`，在 CI 中单独执行
  
  ```java
  @ParameterizedTest
  @ValueSource(ints = {100, 1000, 10000})
  @Tag("performance")
  void test_queryPerformance(int dataSize) {
      // 准备 dataSize 条测试数据
      prepareTestData(dataSize);
      
      long startTime = System.currentTimeMillis();
      mockMvc.perform(get("/orders").param("pageSize", "100"));
      long duration = System.currentTimeMillis() - startTime;
      
      assertTrue(duration < 1000, "查询时间应小于1秒");
  }
  ```
  
  ---
  
  ## 8. 最佳实践速查表
  
  ### 8.1 单元测试速查表
  
  | 检查项 | 是否完成 |
  | :--- | :---: |
  | 使用 `@ExtendWith(MockitoExtension.class)` 而不是 `@SpringBootTest` | ☐ |
  | 所有外部依赖都已 Mock | ☐ |
  | 测试方法命名遵循 `test_{Method}_{Condition}_{Result}` | ☐ |
  | 代码结构清晰分为 Given-When-Then | ☐ |
  | 三验证模型：状态变更、依赖交互、返回值 | ☐ |
  | 测试方法之间无依赖，可独立运行 | ☐ |
  | 测试代码简单，无复杂逻辑 | ☐ |
  
  ### 8.2 接口测试速查表
  
  | 检查项 | 是否完成 |
  | :--- | :---: |
  | 使用真实数据库（H2 或 Testcontainers） | ☐ |
  | 覆盖 1+N+M 场景（成功+参数异常+业务异常） | ☐ |
  | 包含安全对抗测试（SQL注入、越权） | ☐ |
  | 使用 `@Transactional` + `@Rollback` 保证数据隔离 | ☐ |
  | 测试方法命名清晰表达测试场景 | ☐ |
  | 使用 `application-test.yml` 隔离配置 | ☐ |
  | 对于创建/更新接口，验证幂等性 | ☐ |
  
  ### 8.3 功能测试速查表
  
  | 检查项 | 是否完成 |
  | :--- | :---: |
  | 测试完整的业务流程，不是单个接口 | ☐ |
  | 使用四维破坏法推导异常场景 | ☐ |
  | 验证数据守恒（涉及资产流转时） | ☐ |
  | 验证副作用隔离（无关数据未受影响） | ☐ |
  | 模拟外部依赖故障（超时、失败） | ☐ |
  | 使用 BDD 结构（Given-When-Then） | ☐ |
  | 每个测试用例对应一个用户故事 | ☐ |
  
  ### 8.4 通用最佳实践
  
  | 实践 | 说明 |
  | :--- | :--- |
  | **测试独立性** | 每个测试方法可以独立运行，不依赖执行顺序 |
  | **测试可重复性** | 每次运行结果一致，不依赖外部状态 |
  | **测试可读性** | 测试代码应该像文档一样易读 |
  | **测试维护性** | 业务逻辑变更时，测试代码易于修改 |
  | **测试速度** | 单元测试 < 5分钟，接口测试 < 15分钟，功能测试 < 30分钟 |
  | **测试覆盖** | 核心业务逻辑必须 100% 覆盖，非核心代码 ≥ 50% |
  | **测试命名** | 测试方法名应该清晰表达"在什么条件下，期望什么结果" |
  