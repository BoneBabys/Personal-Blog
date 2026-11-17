# 我在中国的记忆 · Astro

基于 Astro 5 的双栏目博客：旅行见闻与专业技能分享彼此独立，分别使用 `/travel/` 与 `/skills/` 路径。

## 本地运行

```sh
npm install
npm run dev
```

访问 Astro 显示的本地地址。构建及预览：`npm run build`、`npm run preview`。

## 内容分类

在 `src/content/blog/` 新建 Markdown 文件，并填写：

- `section: travel` 或 `section: skills`
- `title`、`description`、`pubDate`
- `tags`：旅行文章使用 `travel` 和地点标签；技能文章使用技能类型与工具名
- 旅行文章另加 `image`，指向 `/images/` 下的卡片预览图

技能文章的 Markdown 围栏代码由 Astro/Shiki 在构建时进行语法高亮；文章标题会自动生成目录锚点。RSS 订阅地址为 `/rss.xml`，包含两个栏目文章的分类与永久链接。

RSS 默认站点地址使用 GitHub Pages 项目站点。部署到其他域名时，请在 `astro.config.mjs` 中设置 `site`，RSS 会使用 Astro 的 `SITE` 值。
