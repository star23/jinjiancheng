#!/usr/bin/env python3
"""用 Playwright（真实浏览器）渲染 jinjiancheng.com，过 Cloudflare，爬取全部文章 → 文章/。

官网有 Cloudflare 防护，requests/WebFetch 直接 403；必须用真实浏览器加载、等待挑战通过。

用法:
    pip install playwright && playwright install chromium
    python3 scrape_site_playwright.py                       # 爬全站
    python3 scrape_site_playwright.py --limit 20            # 只抓最新 20 篇（调试）
    python3 scrape_site_playwright.py --headful             # 显示浏览器窗口（人工过验证）
    python3 scrape_site_playwright.py --url https://jinjiancheng.com/posts/xxx  # 抓单页

说明:
  - 站点 DOM 选择器可能与下方默认值不同：先用 --headful 跑一次，按实际结构调整
    LINK_SELECTORS / TITLE_SELECTORS / BODY_SELECTORS / DATE_SELECTORS 即可。
  - 需在【开放网络环境】运行；本 Claude 沙箱出网白名单不含 jinjiancheng.com。
  - 频率不要太高，礼貌爬取（脚本默认每页间隔 2s）。
"""
from __future__ import annotations
import argparse, re, sys, time
from urllib.parse import urljoin, urlparse

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("缺少依赖：pip install playwright && playwright install chromium")

import _common

BASE = "https://jinjiancheng.com/"
# —— 以下选择器按站点实际结构微调 ——
LINK_SELECTORS = ["article a[href]", ".post-list a[href]", "a[href*='/post']", "main a[href]"]
TITLE_SELECTORS = ["h1", ".post-title", "article header h1", "title"]
BODY_SELECTORS = ["article .content", ".post-content", "article", "main"]
DATE_SELECTORS = ["time[datetime]", "time", ".date", ".post-date", ".meta"]


def _first_text(page, selectors):
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el:
                t = (el.get_attribute("datetime") or el.inner_text() or "").strip()
                if t:
                    return t
        except Exception:  # noqa
            continue
    return ""


def _first_html(page, selectors):
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el:
                h = el.inner_html()
                if h and len(h) > 50:
                    return h
        except Exception:  # noqa
            continue
    return ""


def collect_links(page) -> list[str]:
    page.goto(BASE, wait_until="networkidle", timeout=60000)
    _wait_cloudflare(page)
    # 滚动加载（若是无限滚动/懒加载）
    for _ in range(30):
        page.mouse.wheel(0, 4000); page.wait_for_timeout(400)
    hrefs = set()
    for sel in LINK_SELECTORS:
        for el in page.query_selector_all(sel):
            h = el.get_attribute("href") or ""
            full = urljoin(BASE, h)
            if urlparse(full).netloc.endswith("jinjiancheng.com") and full.rstrip("/") != BASE.rstrip("/"):
                hrefs.add(full.split("#")[0])
    return sorted(hrefs)


def _wait_cloudflare(page):
    for _ in range(20):
        html = page.content()
        if "Just a moment" in html or "cf-challenge" in html or "Checking your browser" in html:
            page.wait_for_timeout(1500)
        else:
            return
    print("  ! 可能仍卡在 Cloudflare 挑战，建议 --headful 人工通过")


def scrape_article(page, url, overwrite) -> str:
    page.goto(url, wait_until="networkidle", timeout=60000)
    _wait_cloudflare(page)
    title = _first_text(page, TITLE_SELECTORS)
    date_raw = _first_text(page, DATE_SELECTORS)
    m = re.search(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", date_raw)
    date = m.group(0).replace("/", "-").replace(".", "-") if m else ""
    body_html = _first_html(page, BODY_SELECTORS)
    if not body_html:
        return f"未解析到正文：{url}"
    content = _common.html_to_text(body_html)
    path = _common.write_article_md(title, "金渐成", date, content, source=url, overwrite=overwrite)
    return f"已存在跳过：{title}" if path is None else f"已保存：{path}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="只抓这个单页")
    ap.add_argument("--limit", type=int, default=0, help="最多抓多少篇（0=全部）")
    ap.add_argument("--headful", action="store_true", help="显示浏览器（人工过验证）")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--no-index", action="store_true")
    args = ap.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)
        page = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
            locale="zh-CN").new_page()

        if args.url:
            print(scrape_article(page, args.url, args.overwrite))
        else:
            links = collect_links(page)
            print(f"发现 {len(links)} 个文章链接")
            if args.limit:
                links = links[:args.limit]
            for i, u in enumerate(links):
                try:
                    print(f"[{i+1}/{len(links)}] " + scrape_article(page, u, args.overwrite))
                except Exception as e:  # noqa
                    print(f"[{i+1}/{len(links)}] 出错 {u}: {e}")
                time.sleep(2)
        browser.close()

    if not args.no_index:
        n = _common.rebuild_index()
        print(f"索引已重建，共 {n} 篇。")


if __name__ == "__main__":
    main()
