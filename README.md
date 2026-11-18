# 胡炳坤的个人博客 · Astro

基于 Astro 5 的双栏目个人博客：旅行见闻与专业技能分享彼此独立，分别使用 `/travel/` 与 `/skills/` 路径。

## 页面结构

- `/`：满屏水墨山水背景，中央为 4:3 半透明宣纸入口框，框内含「旅行见闻」「专业技能」两个索引。
- `/travel/`：青绿水墨底，正文与文章列表右置，为画面右侧留白让位。
- `/skills/`：文人极简底，正文左置；背景为左侧焦墨竖笔与笔记横线。
- 全站点击会生成淡出墨点（`src/components/InkClick.astro`）。

## 本地运行

```sh
npm install
npm run dev
```

访问 Astro 显示的本地地址。构建及预览：`npm run build`、`npm run preview`。

## 背景素材

三张背景与三张旅行缩略图由 `scripts/generate-backgrounds.py` 生成，输出为高质量 JPEG：

```sh
python scripts/generate-backgrounds.py
```

脚本使用 Pillow，按「生宣纸底 → 淡墨晕染 → 焦墨细节 → 哑光颗粒」绘制，统一遵守低饱和、避开纯黑与纯白、预留大面积留白。修改配色或构图后重跑即可覆盖 `public/images/` 下的同名文件。

## 内容分类

在 `src/content/blog/` 新建 Markdown 文件，并填写：

- `section: travel` 或 `section: skills`
- `title`、`description`、`pubDate`
- `tags`：旅行文章使用 `travel` 和地点标签；技能文章使用技能类型与工具名
- 旅行文章另加 `image`，指向 `/images/travel/` 下的卡片预览图

技能文章的 Markdown 围栏代码由 Astro/Shiki 在构建时进行语法高亮（`github-light` 浅色主题，配合宣纸底）；文章标题会自动生成目录锚点。

## 文章评论

文章页评论使用 Utterances（基于 GitHub Issues），配置在 `src/config/comments.ts`，页面组件为 `src/components/Comments.astro`。首次启用需要三步：

1. 仓库保持 public，并在仓库 Settings 中确认 Issues 已开启；
2. 打开 <https://github.com/apps/utterances>，把这个 App 安装到 `BoneBabys/Personal-Blog` 仓库；
3. 部署后打开任意文章页，Utterances 会按文章路径自动创建对应 issue。

访客用 GitHub 账号登录后即可留言。若更换仓库，修改 `src/config/comments.ts` 中的 `repo` 即可。

RSS 订阅地址仍为 `/rss.xml`，包含两个栏目文章的分类与永久链接；页脚不再显示订阅入口。RSS 默认站点地址使用 GitHub Pages 项目站点。部署到其他域名时，请在 `astro.config.mjs` 中设置 `site`，RSS 会使用 Astro 的 `SITE` 值。
