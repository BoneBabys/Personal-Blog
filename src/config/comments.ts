/**
 * 文章评论配置（Utterances，基于 GitHub Issues）。
 *
 * 首次启用：
 *  1. 仓库保持 public，并在 Settings → General 中确认 Issues 已开启；
 *  2. 打开 https://github.com/apps/utterances ，把这个 App 安装到本仓库；
 *  3. 访客用 GitHub 账号登录后即可评论，每篇文章按路径自动创建对应 issue。
 *
 * 如果要换仓库，只需修改 repo；issueTerm 建议保持 pathname，
 * 这样同一路径的文章会归到同一个 issue。
 */
export const comments = {
  enabled: true,
  repo: 'BoneBabys/Personal-Blog',
  issueTerm: 'pathname',
  theme: 'github-light',
};
