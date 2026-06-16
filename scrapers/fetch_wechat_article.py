#!/usr/bin/env python3
"""抓取单篇/多篇微信公众号文章（mp.weixin.qq.com/s/...）→ 存为 文章/ 下的 Markdown。

用法:
    python3 fetch_wechat_article.py <url> [<url2> ...]
    python3 fetch_wechat_article.py --file urls.txt          # 每行一个链接
    python3 fetch_wechat_article.py <url> --overwrite         # 覆盖已存在
    python3 fetch_wechat_article.py <url> --no-index          # 不重建索引

依赖: requests（必需）；bs4（可选，解析更稳）。  pip install requests beautifulsoup4

说明:
  - 微信文章页对服务器端爬虫有反爬：建议用移动端 UA、控制频率（脚本默认间隔 3s）。
  - 若返回 “环境异常/请在微信客户端打开”，说明被风控，需降低频率或换出口 IP。
  - 本脚本需在【开放网络环境】运行（本 Claude 沙箱的出网白名单会拦截 mp.weixin.qq.com）。
"""
from __future__ import annotations
import argparse, re, sys, time, datetime

try:
    import requests
except ImportError:
    sys.exit("缺少依赖 requests：pip install requests")

import _common

UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.40")


def _extract(html: str) -> dict:
    """从微信文章 HTML 抽取 标题/作者/日期/正文。优先 bs4，回退正则。"""
    title = author = date = ""
    body_html = ""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        el = soup.select_one("#activity-name, h1.rich_media_title")
        if el: title = el.get_text(strip=True)
        el = soup.select_one("#js_name, #js_author, .rich_media_meta_text")
        if el: author = el.get_text(strip=True)
        node = soup.select_one("#js_content, .rich_media_content")
        if node:
            for bad in node.select("script, style"):
                bad.decompose()
            body_html = str(node)
    except ImportError:
        m = re.search(r'id="activity-name"[^>]*>(.*?)<', html, re.S)
        if m: title = re.sub(r"\s+", " ", m.group(1)).strip()
        m = re.search(r'id="js_name"[^>]*>(.*?)<', html, re.S)
        if m: author = re.sub(r"\s+", " ", m.group(1)).strip()
        m = re.search(r'(?is)<div[^>]+id="js_content".*?</div>\s*(?=<script|<div id="js_)', html)
        body_html = m.group(0) if m else ""

    if not title:
        m = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        if m: title = m.group(1).strip()

    # 发布时间：多种形态
    for pat in [r'var ct = "(\d{10})"', r'var createTime\s*=\s*[\'"]([^\'"]+)',
                r'id="publish_time"[^>]*>([\d\-: ]+)<', r't="(\d{10})"']:
        m = re.search(pat, html)
        if m:
            v = m.group(1)
            if v.isdigit() and len(v) == 10:
                date = datetime.datetime.fromtimestamp(int(v)).strftime("%Y-%m-%d")
            else:
                date = v.strip()[:10]
            break
    return {"title": title, "author": author or "金渐成",
            "date": date, "body_html": body_html}


def fetch_one(url: str, session: requests.Session, overwrite: bool) -> str:
    r = session.get(url, headers={"User-Agent": UA_MOBILE,
                                  "Referer": "https://mp.weixin.qq.com/"}, timeout=20)
    r.encoding = "utf-8"
    if r.status_code != 200:
        return f"HTTP {r.status_code}  {url}"
    if "请在微信客户端打开" in r.text or "环境异常" in r.text:
        return f"被风控（环境异常）  {url}"
    info = _extract(r.text)
    if not info["body_html"]:
        return f"未能解析正文（页面结构可能变化）  {url}"
    content = _common.html_to_text(info["body_html"])
    path = _common.write_article_md(info["title"], info["author"], info["date"],
                                    content, source=url, overwrite=overwrite)
    if path is None:
        return f"已存在，跳过：{info['date']} {info['title']}"
    return f"已保存：{path}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--file", help="包含链接的文本文件，每行一个")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--no-index", action="store_true")
    ap.add_argument("--delay", type=float, default=3.0, help="请求间隔秒数（防风控）")
    args = ap.parse_args()

    urls = list(args.urls)
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            urls += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    if not urls:
        ap.error("请提供至少一个微信文章链接，或用 --file 指定列表")

    s = requests.Session()
    for i, u in enumerate(urls):
        print(fetch_one(u, s, args.overwrite))
        if i < len(urls) - 1:
            time.sleep(args.delay)
    if not args.no_index:
        n = _common.rebuild_index()
        print(f"索引已重建，共 {n} 篇。")


if __name__ == "__main__":
    main()
