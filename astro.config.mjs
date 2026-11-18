import { defineConfig } from 'astro/config';

export default defineConfig({
  markdown: {
    shikiConfig: {
      // 浅色代码主题，与宣纸底、墨色文字统一
      theme: 'github-light',
      wrap: true,
    },
  },
});
