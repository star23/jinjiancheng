# 抓取脚本（同步金渐成最新文章）

把金渐成文章同步到最新状态的四种抓取方式。输出统一写入仓库根目录的 `文章/` 目录，
文件名 `YYYY-MM-DD 标题.md`，格式与既有存档一致，并自动重建 `文章/README.md` 索引。

> ⚠️ **必须在开放网络环境运行**（你自己的机器/服务器）。
> 如果运行环境禁止外网访问，`jinjiancheng.com`、`mp.weixin.qq.com`、RSS 桥等域名可能会被拦截；
> 请在可联网环境运行。微信仍可能触发反爬，优先使用官网静态页同步。

## 安装

```bash
pip install -r requirements.txt
# 如用官网 Playwright 方案，额外：
playwright install chromium
```

## 四种方式

### 0. 官网静态页整站 — `scrape_site_static.py`（推荐）
直接抓取 `https://jinjiancheng.com/articles` 分页和单篇文章页。当前官网文章列表与正文都在
HTML 中直接返回，因此不需要 Playwright，也不需要手工提供微信链接。
```bash
python3 scrape_site_static.py                 # 全站同步
python3 scrape_site_static.py --limit 30      # 只抓最新 30 篇
python3 scrape_site_static.py --overwrite     # 覆盖同名文件
```
- 默认会按“标题规范化 + 日期相差不超过 3 天”跳过旧存档中的近似文章，避免旧数据日期差 1 天或标题末尾 `~` 造成重复。
- 若官网结构改版导致正文不在 `article div.prose` 中，再考虑方式 3 的 Playwright 方案。

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
用真实浏览器渲染官网页面。当前仅作为静态页方案失效后的备用方案。
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
