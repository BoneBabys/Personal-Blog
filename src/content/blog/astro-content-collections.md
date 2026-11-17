---
title: "用 Astro 内容集合搭建可维护的双栏目博客"
description: "从内容分类、静态路由到代码高亮与目录导航，整理一个可持续扩展的 Astro 实践。"
pubDate: 2025-04-22
section: skills
tags:
  - frontend
  - astro
---

当一个博客同时记录旅行与技术时，最重要的是让两种内容各自清晰，而不是让它们互相抢占读者的注意力。本文用 Astro 内容集合、独立路由和 Markdown 内容建立清楚的边界。

## 1. 用 frontmatter 明确分类

给每篇文章声明唯一栏目，列表页就能稳定筛选，也能避免旅行文章出现在技术推荐中：

```ts
const travel = posts.filter((post) => post.data.section === 'travel');
const skills = posts.filter((post) => post.data.section === 'skills');
```

可以在内容 schema 中用枚举检查分类，并要求标签遵循约定。旅行文章使用 `travel` 与城市或地点标签；技能文章使用技术类型与工具标签。

## 2. 为栏目建立独立路由

使用 `/travel/` 与 `/skills/` 作为列表入口，详情页也分别落在各自路径下。首页只做并列入口，不在栏目之间放置“猜你喜欢”或交叉推荐。旧文章地址可通过永久重定向兼容，避免已有链接失效。

## 3. 让 Markdown 负责内容

Astro 的 Markdown 构建流程会为围栏代码块生成语法高亮；保留代码语言标注有助于主题正确识别：

```astro
---
const title = 'Readable by default';
---

<h1>{title}</h1>
```

内容 schema、列表与页面模板保持分离，新增文章只需创建 Markdown 文件，不必复制整页布局。

## 4. 生成可跳转的目录

渲染内容时可以读取标题元数据，再按 heading slug 链接到正文锚点：

```astro
const { Content, headings } = await render(post);

// 在目录中将标题链接到 `#${heading.slug}`
```

移动端可将目录放在正文之前，桌面端则固定在侧栏。检查每个标题都有唯一 slug，并保证目录链接具有足够的触控区域。

## 上线前检查

- 旅行与技能页面各自只查询自己的内容类型。
- 页面 title、description 和 canonical URL 与栏目路径一致。
- RSS 中每篇文章包含永久链接、发布日期和栏目分类。
- 手机屏幕下代码块可横向滚动，目录不挤压正文。
