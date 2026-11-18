---
title: "Redis 缓存实践：从缓存穿透到一致性"
description: "结合常见读多写少场景，梳理 Redis 缓存键设计、失效策略、穿透保护与数据一致性取舍。"
pubDate: 2025-05-06
section: skills
tags:
  - caching
  - redis
---

Redis 通常被用作数据库前的一层高速缓存，但真正可靠的缓存方案不止是 `GET` 和 `SET`。本文以商品详情读取为例，介绍一套易于理解、可逐步演进的实践。代码仅作结构示例，具体过期时间和一致性策略应结合业务评估。

## 1. 设计清晰的缓存键

缓存键应包含业务域、实体类型和稳定 ID，避免不同数据共用命名空间。对外部输入先做校验，不要直接把任意用户字符串拼接成键。

```text
product:detail:{productId}
```

给键设置合理的过期时间，并加入小幅随机抖动，可以减少大量键同时到期造成的瞬时回源压力。

## 2. 使用 Cache-Aside 读取

Cache-Aside（旁路缓存）由应用负责查询缓存、回源数据库并填充缓存：

```ts
async function getProduct(id: string) {
  const key = `product:detail:${id}`;
  const cached = await redis.get(key);

  if (cached !== null) {
    return JSON.parse(cached);
  }

  const product = await database.product.findUnique({ where: { id } });
  if (product === null) {
    return null;
  }

  await redis.set(key, JSON.stringify(product), { EX: 300 });
  return product;
}
```

实际项目中还要处理 JSON 反序列化失败、缓存服务超时和并发回源。缓存不可用时是否降级直查数据库，要依据数据库容量与业务优先级决定。

## 3. 防护缓存穿透与击穿

缓存穿透指请求持续查询不存在的数据。可以对经过校验的不存在结果短暂缓存空值，或使用布隆过滤器做前置判断；空值 TTL 应较短，避免新增数据后长时间不可见。

缓存击穿通常发生在热点键失效时，大量请求同时回源。可按需使用短时互斥锁、请求合并或逻辑过期。锁必须有过期时间，并设计好获取失败时的退避策略，避免把锁变成新的故障点。

## 4. 更新数据时考虑一致性

常见做法是先更新数据库，再删除对应缓存：

```ts
await database.product.update({ where: { id }, data: changes });
await redis.del(`product:detail:${id}`);
```

这能让后续读取重新加载较新的数据，但并非严格强一致方案。并发读写、删除失败或消息延迟仍可能留下短暂旧值。对更高一致性要求的系统，应考虑重试与补偿、变更事件或版本号，并明确可接受的不一致窗口。

## 5. 监控和上线检查

上线前至少观察缓存命中率、Redis 延迟、错误率、内存使用与淘汰情况，并确认数据库能够承受缓存失效时的回源流量。TTL、淘汰策略和连接池参数都应基于真实负载压测，而不是直接照搬示例。

缓存优化的重点不是让每个请求都命中 Redis，而是在可接受的一致性与复杂度下，稳定地减少不必要的数据库工作。
