#!/usr/bin/env python3
"""通过【公众号 RSS 源】增量同步金渐成文章 → 文章/ 下的 Markdown。

适用于把《金渐成》《天机奇谈》两个公众号接入 RSS 后，定期拉取最新文章。

用法:
    python3 wechat_rss_sync.py <feed_url> [<feed_url2> ...]
    python3 wechat_rss_sync.py <feed_url> --refetch     # 正文不全时回源抓原文页
    python3 wechat_rss_sync.py <feed_url> --no-index

依赖: requests（必需）；feedparser（推荐，解析更稳）。
      pip install requests feedparser

怎么得到公众号的 RSS 源（任选其一，都需自己有可联网的机器/服务器）:
  1) wechat2rss（自建，最稳）   : https://github.com/ttttmr/wechat2rss
  2) RSSHub 的微信路由/转译     : https://docs.rsshub.app  （部分需配合 wechat2rss）
  3) werss / feeddd 等托管服务  : 注册后获取该公众号的 feed 链接
  得到形如 https://<你的实例>/feed/<id>.xml 的地址后，传给本脚本即可。

说明: 本脚本同样需在【开放网络环境】运行；本 Claude 沙箱会拦截相关域名。
"""
from __future__ import annotations
import argparse, re, sys, datetime

try:
    import requests
except ImportError:
    sys.exit("缺少依赖 requests：pip install requests")

import _common

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"


def parse_feed(xml: str) -> list[dict]:
    """优先 feedparser；否则用极简正则解析 RSS/Atom。"""
    items = []
    try:
        import feedparser
        d = feedparser.parse(xml)
        for e in d.entries:
            date = ""
            if getattr(e, "published_parsed", None):
                date = datetime.datetime(*e.published_parsed[:6]).strftime("%Y-%m-%d")
            body = ""
            if getattr(e, "content", None):
                body = e.content[0].value
            elif getattr(e, "summary", None):
                body = e.summary
            items.append({"title": getattr(e, "title", ""), "link": getattr(e, "link", ""),
                          "date": date, "author": getattr(e, "author", ""), "body_html": body})
        return items
    except ImportError:
        pass
    for block in re.findall(r"(?is)<(?:item|entry)\b.*?</(?:item|entry)>", xml):
        def g(tag):
            m = re.search(rf"(?is)<{tag}[^>]*>(.*?)</{tag}>", block)
            return m.group(1).strip() if m else ""
        title = re.sub(r"(?is)<!\[CDATA\[|\]\]>", "", g("title"))
        link = g("link") or (re.search(r'href="([^"]+)"', block) or [None, ""])[1]
        body = re.sub(r"(?is)<!\[CDATA\[|\]\]>", "", g("content:encoded") or g("description") or g("content"))
        raw = g("pubDate") or g("published") or g("updated")
        date = ""
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
        if m:
            date = m.group(0)
        else:  # RFC822: Wed, 29 Apr 2026 ...
            m = re.search(r"(\d{1,2}) (\w{3}) (\d{4})", raw)
            if m:
                try:
                    date = datetime.datetime.strptime(m.group(0), "%d %b %Y").strftime("%Y-%m-%d")
                except ValueError:
                    pass
        items.append({"title": title, "link": link, "date": date, "author": "", "body_html": body})
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("feeds", nargs="+", help="一个或多个 RSS/Atom 源地址")
    ap.add_argument("--refetch", action="store_true", help="正文过短时回源抓微信原文页")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--no-index", action="store_true")
    args = ap.parse_args()

    s = requests.Session()
    added = 0
    for feed in args.feeds:
        try:
            xml = s.get(feed, headers={"User-Agent": UA}, timeout=30).text
        except Exception as e:  # noqa
            print(f"拉取失败 {feed}: {e}"); continue
        items = parse_feed(xml)
        print(f"源 {feed}: 解析到 {len(items)} 条")
        for it in items:
            content = _common.html_to_text(it["body_html"])
            if args.refetch and len(content) < 200 and it["link"]:
                try:
                    import fetch_wechat_article as fw
                    print("  回源:", fetch_one := fw.fetch_one(it["link"], s, args.overwrite))
                    continue
                except Exception as e:  # noqa
                    print("  回源失败:", e)
            path = _common.write_article_md(it["title"], it["author"] or "金渐成",
                                            it["date"], content,
                                            source=it["link"] or feed, overwrite=args.overwrite)
            if path:
                added += 1
                print("  +", path)
    print(f"新增/更新 {added} 篇。")
    if not args.no_index:
        n = _common.rebuild_index()
        print(f"索引已重建，共 {n} 篇。")


if __name__ == "__main__":
    main()
