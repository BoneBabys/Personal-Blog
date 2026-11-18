import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';

const escapeXml = (value: string) => value.replace(/[<>&'\"]/g, (char) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '\"': '&quot;' })[char] ?? char);

export const GET: APIRoute = async () => {
  const posts = (await getCollection('blog')).sort((a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf());
  const siteUrl = import.meta.env.SITE ?? 'https://bonebabys.github.io/Personal-Blog';
  const items = posts.map((post) => {
    const path = `/${post.data.section}/${post.id}/`;
    return `<item><title>${escapeXml(post.data.title)}</title><description>${escapeXml(post.data.description)}</description><link>${siteUrl}${path}</link><guid isPermaLink="true">${siteUrl}${path}</guid><pubDate>${post.data.pubDate.toUTCString()}</pubDate><category>${escapeXml(post.data.section)}</category></item>`;
  }).join('');
  const xml = `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>胡炳坤的个人博客</title><description>旅行见闻与专业技能分享</description><link>${siteUrl}</link><language>zh-CN</language>${items}</channel></rss>`;
  return new Response(xml, { headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' } });
};
