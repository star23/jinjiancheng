# 抓取脚本（同步金渐成最新文章）

把金渐成文章同步到最新状态的三种抓取方式。输出统一写入仓库根目录的 `文章/` 目录，
文件名 `YYYY-MM-DD 标题.md`，格式与既有存档一致，并自动重建 `文章/README.md` 索引。

> ⚠️ **必须在开放网络环境运行**（你自己的机器/服务器）。
> Claude Code 沙箱的**出网白名单**会拦截 `jinjiancheng.com`、`mp.weixin.qq.com`、RSS 桥等域名
> （实测返回 `Host not in allowlist`）；即便放行，官网有 Cloudflare、微信有反爬，仍需下列方式。

## 安装

```bash
pip install -r requirements.txt
# 如用官网 Playwright 方案，额外：
playwright install chromium
```

## 三种方式

### 1. 单篇微信文章 — `fetch_wechat_article.py`
最简单，适合手动补单篇（如你给的链接）。
```bash
python3 fetch_wechat_article.py "https://mp.weixin.qq.com/s/V4UcGvXO6_kJ0jJ-ezf_ug"
python3 fetch_wechat_article.py --file urls.txt        # 批量，每行一个链接
```
- 用移动端 UA、默认每篇间隔 3s 防风控。
- 若提示「被风控（环境异常）」→ 降低频率 / 换出口 IP / 改用方式 3 的 RSS。

### 2. 公众号 RSS 增量同步 — `wechat_rss_sync.py`（推荐做"保鲜"）
把《金渐成》《天机奇谈》接入 RSS 后，定期增量拉取，已存在的自动跳过。
```bash
python3 wechat_rss_sync.py "https://<你的实例>/feed/<id>.xml"
python3 wechat_rss_sync.py "<feed1>" "<feed2>" --refetch   # 正文不全时回源抓原文
```
**怎么拿到公众号 RSS 源**（任选其一，均需自己有可联网机器/服务）：
- **wechat2rss**（自建，最稳）：https://github.com/ttttmr/wechat2rss
- **RSSHub** 微信路由：https://docs.rsshub.app （部分需配合 wechat2rss）
- **werss / feeddd** 等托管服务：注册后获取该公众号 feed 链接

### 3. 官网整站 — `scrape_site_playwright.py`
用真实浏览器渲染、过 Cloudflare，爬取 jinjiancheng.com 全部文章。
```bash
python3 scrape_site_playwright.py --limit 20            # 先小批量调试
python3 scrape_site_playwright.py --headful             # 卡验证时人工通过
python3 scrape_site_playwright.py                       # 全站
```
- 站点 DOM 选择器可能变化：先 `--headful` 跑一次，按实际结构调整脚本顶部的
  `LINK_SELECTORS / TITLE_SELECTORS / BODY_SELECTORS / DATE_SELECTORS`。

## 自动保鲜（可选）
在自己的服务器上挂 cron（例：每天凌晨同步 RSS）：
```cron
0 3 * * *  cd /path/to/jinjiancheng/scrapers && python3 wechat_rss_sync.py "<feed_url>" >> sync.log 2>&1
```
随后 `git add 文章 && git commit && git push` 即可把更新推回仓库。

## 文件
- `_common.py` — 共享：MD 落盘、文件名清洗、HTML→文本、索引重建
- `fetch_wechat_article.py` — 方式 1
- `wechat_rss_sync.py` — 方式 2
- `scrape_site_playwright.py` — 方式 3
- `requirements.txt` — 依赖

> 注：以上脚本在本次会话的沙箱内**无法联网验证**（域名被白名单拦截）；
> 离线部分（解析/落盘/索引）已通过自测。请在开放网络环境首跑时按提示微调选择器。
