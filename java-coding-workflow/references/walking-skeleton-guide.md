# Walking Skeleton 操作指南

## 什么是 Walking Skeleton

"行走的骨架"（Walking Skeleton）是指一个**可以编译、可以启动、端点可以调用**但**核心业务逻辑尚未实现**的代码版本。

类比建筑：先搭钢骨架，确认结构正确，再砌墙装修。

## 为什么先骨架后血肉

| 直接 TDD 完整实现 | 先骨架后血肉 |
|------------------|-------------|
| 写测试时接口签名可能不对 → 反复改测试 | 先确定签名，测试只写一次 |
| 依赖注入错误到最后才发现 | 骨架阶段就验证了注入 |
| 模块间编译依赖问题阻塞全部功能 | 骨架阶段统一解决 |
| 看不出进度 | 功能点状态表清晰 |

## 骨架阶段做什么

### 创建的文件类型

```
Controller     → 端点签名完整，方法体调 Service 后 return null
Service 接口   → 方法签名完整
Service Impl   → 方法体 return null 或 throw UnsupportedOperationException
DTO/Req/Res    → 字段完整 + Lombok @Data
Config         → @Value 字段完整 + 默认值
Client         → 方法签名完整，方法体 return null
```

### 骨架阶段不做什么

- 不写数据库查询逻辑
- 不调上游服务
- 不写异常分支
- 不写缓存逻辑
- 不写业务计算

## 骨架示例

### Controller 骨架

```java
@PostMapping("/combined/preview")
@ResponseBody
public Object previewCombined(@RequestBody CombinedContractDownloadParam param) {
    param.check();
    Map<String, Object> result = new HashMap<>();
    result.put("code", 0);
    result.put("message", "success");
    result.put("data", null); // 骨架：返回 null，端点可调
    return result;
}
```

### Service Impl 骨架

```java
@Component
public class CombinedContractDownloadServiceImpl extends BaseDownloadServiceImpl {

    @Resource
    private CombinedDownloadApolloConfig config;

    @Override
    public void handleSubTask(AsyncTask task, List<AsyncSubTask> subTasks) {
        // 骨架：不做任何处理，编译通过即可
        throw new UnsupportedOperationException("TODO: Phase 2 实现");
    }
}
```

### Config 骨架

```java
@Data
@Component
public class CombinedDownloadApolloConfig {
    @Value("${contract.download.combined.uid.limit:50}")
    private Integer combinedUidLimit;
    // ... 所有配置项完整
}
```

## 骨架阶段完成标准

- [ ] `mvn compile` 通过
- [ ] 所有 Controller 端点可访问（返回固定值或错误页）
- [ ] 所有 @Resource/@Autowired 注入无异常
- [ ] 功能点状态表已产出并向用户展示
- [ ] 用户已确认状态表

## 常见问题

**Q: 某功能点逻辑很简单（纯校验），骨架即完整怎么办？**
直接标 ✅，在状态表说明列写"骨架即完整"。

**Q: 骨架阶段发现技术方案设计有问题怎么办？**
暂停编码，记录到 decisions.md，回退到技术方案阶段。

**Q: 是否可以跨 Phase？**
不可以。必须先完成 Phase 1 全部步骤（包括用户确认状态表），再进入 Phase 2。
