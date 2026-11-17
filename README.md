# Personal Blog

A minimal personal blog built with Astro. Blog posts are Markdown files and are rendered as static pages at build time.

## Get started

```sh
npm install
npm run dev
```

Open the local URL printed by Astro. Build the site with `npm run build` and preview the production build with `npm run preview`.

## Customize

- Replace `Your Name` in `src/pages/index.astro` and `src/pages/blog/[...slug].astro`.
- Update the contact email and GitHub link in `src/pages/index.astro`.
- Add a Markdown file in `src/content/blog/` with frontmatter fields `title`, `description`, `pubDate`, and optional `tags`.
- Adjust the colors and typography in `src/styles/global.css`.

Example post frontmatter:

```yaml
---
title: "A new post"
description: "A short summary for the post list and search engines."
pubDate: 2026-11-17
tags:
  - notes
---

Write your post here.
```
