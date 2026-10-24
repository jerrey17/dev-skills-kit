# 新增测试开发 -- 常见陷阱与反模式

> **加载时机**: 每个测试设计与编码阶段都应参考本文件，避免已知失败模式。

---

## 1. Mock 而非真实行为

**陷阱描述**: 测试验证的是 mock 对象的行为，而非被测代码的真实逻辑。

**典型表现**:
```java
// BAD: 测试的是 mock 的返回值，不是业务逻辑
@Test
void test_getOrderTotal() {
    OrderService mockService = mock(OrderService.class);
    when(mockService.getTotal("id")).thenReturn(100.0);
    assertEquals(100.0, mockService.getTotal("id")); // 测试 mock，毫无意义
}
```

**正确做法**: Mock 外部依赖（Repository/RPC），不 mock 被测对象本身。用 `@InjectMocks` 注入真实被测对象。

**检测方法**: 如果删除被测类的全部业务逻辑，测试仍然通过，说明你在测 mock。

---

## 2. 测试名称模糊

**陷阱描述**: 测试方法名无法描述测试场景，失败时无法从方法名判断问题。

**典型表现**:
```java
@Test void test1() { ... }
@Test void testOrder() { ... }
@Test void testSuccess() { ... }
```

**正确做法**: 遵循 `test_{Method}_{Condition}_{ExpectedResult}` 格式。

**检测方法**: 不看测试代码，仅凭方法名能否说清"测什么场景、期望什么结果"。

---

## 3. 断言缺失（The Free Rider）

**陷阱描述**: 测试方法中没有任何 assert/verify 语句，测试永远通过。

**典型表现**:
```java
@Test
void test_createOrder() {
    orderService.create(request);
    // 没有断言！无论代码是否正确，测试永远绿色
}
```

**正确做法**: 每个 @Test 方法至少包含一个有效断言。推荐使用三验证模型覆盖多个维度。

**检测方法**: 全局搜索不包含 assert/verify/assertThrows 的 @Test 方法。

---

## 4. 测试之间有隐式依赖

**陷阱描述**: 测试方法共享可变状态，执行顺序改变会导致测试失败。

**典型表现**:
```java
private static Order sharedOrder; // 类级别共享可变状态

@Test void test1_createOrder() { sharedOrder = orderService.create(...); }
@Test void test2_cancelOrder() { orderService.cancel(sharedOrder.getId()); } // 依赖 test1
```

**正确做法**: 每个测试方法独立准备自己的数据。使用 @BeforeEach 重置状态。

**检测方法**: 单独运行每个测试方法，看是否都能独立通过。

---

## 5. 过度 Mock（The Mockery）

**陷阱描述**: Mock 设置代码远超测试逻辑，测试变成了"配置 Mock 的测试"。

**信号**: mock 设置行数 > 断言行数的 2 倍以上。

**正确做法**:
- 只 Mock 直接外部依赖，不 Mock 被测类的内部方法
- 如果 mock 太多，考虑被测类是否耦合过重
- 对于复杂场景，考虑使用集成测试替代

---

## 6. 只测 Happy Path

**陷阱描述**: 只写了正常路径的测试，忽略异常路径、边界值和错误处理。

**检测方法**: 检查测试清单是否覆盖了 1+N 模式中的所有 N 维度（输入异常/状态异常/权限异常/依赖故障）。

**正确做法**: 对每个被测方法，系统性推导异常路径，确保 assertThrows 场景有覆盖。

---

## 7. 接口测试只校验状态码

**陷阱描述**: 接口测试只验证 HTTP Status Code，不校验响应体内容和数据库状态。

**典型表现**:
```java
mockMvc.perform(post("/orders").content(body))
    .andExpect(status().isCreated()); // 只校验 201，不看响应内容
```

**正确做法**: 必须同时校验状态码、响应体关键字段、数据库持久化结果。

---

## 8. 功能测试退化为接口测试

**陷阱描述**: 功能测试只是顺序调用多个接口，但没有验证跨接口的数据流转和状态变迁。

**正确做法**: 功能测试的核心价值是验证端到端业务闭环。每一步之后都要断言中间状态，验证数据在各环节的正确流转。

---

## 9. 在单元测试中启动 Spring Context

**陷阱描述**: 使用 @SpringBootTest 或 @MockBean 导致单元测试启动慢、依赖重。

**正确做法**: 单元测试使用 `@ExtendWith(MockitoExtension.class)` + `@Mock` + `@InjectMocks`，保持毫秒级执行速度。

---

## 10. 测试数据污染

**陷阱描述**: 接口测试或功能测试写入数据库后未清理，影响后续测试。

**正确做法**: 使用 `@Transactional` + `@Rollback` 自动回滚，或在 @AfterEach 中显式清理。

---

## 11. The Liar（说谎者）

**陷阱描述**: 测试通过了但实际验证的不是预期行为。测试名说"验证取消"，断言却在检查创建。

**典型表现**:
```java
@Test
void test_cancel_whenPending_shouldChangeStatus() {
    Order order = new Order("id", OrderStatus.PENDING);
    order.cancel();
    assertNotNull(order); // 断言与"取消"行为无关！永远通过
}
```

**正确做法**: 断言必须精确校验被测行为的核心结果。上例应断言 `assertEquals(OrderStatus.CANCELED, order.getStatus())`。

**检测方法**: 修改被测方法的核心逻辑（如 cancel() 不再改变状态），看测试是否失败。如果不失败，说明你在测谎。

---

## 12. The Giant（巨人）

**陷阱描述**: 单个测试方法验证了过多行为，失败时无法从方法名和错误信息定位问题。

**典型表现**:
```java
@Test
void test_orderProcess() {
    Order order = orderService.create(request);
    assertNotNull(order);
    orderService.pay(order.getId());
    assertEquals(OrderStatus.PAID, order.getStatus());
    orderService.ship(order.getId());
    assertEquals(OrderStatus.SHIPPED, order.getStatus());
    // ... 继续 20 行断言
}
```

**正确做法**: 方法名包含"and"或断言超过 5 个时，拆分为多个独立测试。每个 @Test 只验证一个行为。

**检测方法**: 测试方法名是否能用一句话描述？如果需要"并且"来串联，就应该拆分。

---

## 13. The Inspector（窥探者）

**陷阱描述**: 测试过度耦合实现细节（反射访问私有方法、验证内部调用顺序），导致重构即破坏测试。

**典型表现**:
```java
@Test
void test_calculateTotal() {
    Method privateMethod = OrderService.class.getDeclaredMethod("internalCalc", BigDecimal.class);
    privateMethod.setAccessible(true);
    BigDecimal result = (BigDecimal) privateMethod.invoke(service, new BigDecimal("100"));
    assertEquals(new BigDecimal("90"), result);
}
```

**正确做法**: 只通过公共接口测试。私有方法是实现细节，通过调用公共方法间接验证其正确性。

**检测方法**: 如果只重构内部实现（不改变公共接口行为），测试是否会失败？如果会，说明你在窥探实现。

---

## 14. The Nitpicker（过度精确匹配）

**陷阱描述**: 测试断言了完整输出结构，但实际只关心个别字段。不相关字段的变更导致测试频繁失败。

**典型表现**:
```java
@Test
void test_createOrder() {
    Order order = orderService.create(request);
    // 断言整个 toString()，任何字段变化都导致失败
    assertEquals("Order{id=1, status=PENDING, userId=user1, createTime=2024-01-01...}", order.toString());
}
```

**正确做法**: 只断言与被测行为直接相关的字段：`assertEquals(OrderStatus.PENDING, order.getStatus())`。

---

## 速查表：写测试前的自检

| # | 检查项 | 通过标准 | 对应陷阱 |
|---|--------|----------|----------|
| 1 | 测试名能描述场景吗？ | 不看代码，方法名就能说清测什么 | #2 名称模糊 |
| 2 | 有有效断言吗？ | 至少一个 assert/verify/assertThrows | #3 Free Rider |
| 3 | 断言验证的是真实行为吗？ | 修改业务逻辑后测试应失败 | #11 The Liar |
| 4 | Mock 的是依赖不是被测对象？ | 删除业务代码后测试应该失败 | #1 Mock 而非真实行为 |
| 5 | Mock 数量合理吗？ | mock 设置行数 <= 断言行数的 2 倍 | #5 过度 Mock |
| 6 | 测试独立吗？ | 单独运行能通过，不依赖执行顺序 | #4 隐式依赖 |
| 7 | 异常路径覆盖了吗？ | 不只有 Happy Path | #6 只测 Happy Path |
| 8 | 断言具体吗？ | 校验具体字段值，不是 assertNotNull | #14 Nitpicker |
| 9 | 测试足够小吗？ | 单个 @Test 不超过 5 个断言 | #12 The Giant |
| 10 | 只测公共接口吗？ | 无反射、无私有方法直接调用 | #13 The Inspector |
| 11 | 接口测试校验了响应体吗？ | 不只校验 status code | #7 只校验状态码 |
| 12 | 测试数据已清理吗？ | @Transactional/@Rollback 或显式清理 | #10 数据污染 |
