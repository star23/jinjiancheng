#!/usr/bin/env python3
"""直接抓取 jinjiancheng.com 静态文章页，写入仓库根目录的 文章/。

站点的 /articles 分页和单篇文章页当前都能返回完整 HTML，不需要 Playwright。
脚本会：
  1. 从 /articles 和 /articles/p/N 收集全部文章 URL；
  2. 抽取单篇页 article > header 与 div.prose；
  3. 写入 YYYY-MM-DD 标题.md，并重建 文章/README.md；
  4. 对已有旧存档做标题+日期近邻去重，避免因日期差 1 天或标题末尾波浪号产生重复。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from datetime import date
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("缺少依赖：pip install requests beautifulsoup4")

import _common

BASE = "https://jinjiancheng.com"
LIST_URL = f"{BASE}/articles"
ARTICLE_RE = re.compile(r"^/articles/(jinjiancheng|tianjiqitan)/(\d{4}-\d{2}-\d{2})(?:-\d+)?$")
PAGE_RE = re.compile(r"^/articles/p/(\d+)$")
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def normalize_title(title: str) -> str:
    title = re.sub(r"[~～]+$", "", title or "").strip()
    title = re.sub(r"\s+", "", title)
    return title


def days_between(a: str, b: str) -> int | None:
    try:
        return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)
    except ValueError:
        return None


def existing_title_dates(out_dir: str) -> dict[str, list[str]]:
    seen: dict[str, list[str]] = {}
    if not os.path.isdir(out_dir):
        return seen
    for fn in os.listdir(out_dir):
        if not fn.endswith(".md") or fn == "README.md":
            continue
        path = os.path.join(out_dir, fn)
        fm = _common._read_frontmatter(path)
        title = fm.get("title") or fn[11:-3]
        article_date = fm.get("date") or fn[:10]
        seen.setdefault(normalize_title(title), []).append(article_date)
    return seen


def fetch(session: requests.Session, url: str, timeout: float, retries: int) -> str:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, timeout=timeout)
            r.raise_for_status()
            if "Just a moment" in r.text or "cf-challenge" in r.text:
                raise RuntimeError(f"Cloudflare challenge: {url}")
            return r.text
        except Exception as e:  # noqa: BLE001
            last_error = e
            if attempt < retries:
                time.sleep(min(2 * attempt, 8))
    raise RuntimeError(f"请求失败 {url}: {last_error}")


def collect_links(session: requests.Session, timeout: float, retries: int) -> list[str]:
    first_html = fetch(session, LIST_URL, timeout, retries)
    first_soup = BeautifulSoup(first_html, "html.parser")
    pages = {1}
    for a in first_soup.select("a[href]"):
        href = a.get("href") or ""
        m = PAGE_RE.match(urlparse(href).path)
        if m:
            pages.add(int(m.group(1)))

    links: dict[str, str] = {}
    for page_no in range(1, max(pages) + 1):
        url = LIST_URL if page_no == 1 else f"{LIST_URL}/p/{page_no}"
        print(f"扫描列表页 {page_no}/{max(pages)}: {url}", flush=True)
        soup = first_soup if page_no == 1 else BeautifulSoup(
            fetch(session, url, timeout, retries), "html.parser"
        )
        for a in soup.select("a[href]"):
            href = a.get("href") or ""
            path = urlparse(href).path
            if ARTICLE_RE.match(path):
                links[path] = urljoin(BASE, path)
    return [links[path] for path in sorted(links)]


def parse_article(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("main article")
    if not article:
        raise ValueError("未找到 main article")

    title_el = article.select_one("h1")
    prose = article.select_one("div.prose")
    if not title_el or not prose:
        raise ValueError("未找到标题或正文 div.prose")

    path = urlparse(url).path
    m = ARTICLE_RE.match(path)
    if not m:
        raise ValueError(f"非文章 URL: {url}")
    slug, article_date = m.groups()
    author = "金渐成" if slug == "jinjiancheng" else "天机奇谈"
    title = title_el.get_text(" ", strip=True)
    content = _common.html_to_text(str(prose))
    if len(content) < 80:
        raise ValueError("正文过短，疑似解析失败")

    return {
        "title": title,
        "author": author,
        "date": article_date,
        "content": content,
        "source": url,
    }


def should_skip_existing(info: dict, seen: dict[str, list[str]], window_days: int) -> bool:
    title_key = normalize_title(info["title"])
    for old_date in seen.get(title_key, []):
        delta = days_between(old_date, info["date"])
        if delta is not None and delta <= window_days:
            return True
    return False


def article_sort_key(url: str) -> tuple[str, str]:
    m = ARTICLE_RE.match(urlparse(url).path)
    if not m:
        return ("0000-00-00", url)
    return (m.group(2), url)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="最多抓多少篇（0=全部）")
    ap.add_argument("--delay", type=float, default=0.2, help="每篇文章间隔秒数")
    ap.add_argument("--timeout", type=float, default=60.0, help="单次请求超时秒数")
    ap.add_argument("--retries", type=int, default=3, help="单个 URL 最大重试次数")
    ap.add_argument("--overwrite", action="store_true", help="覆盖相同文件名")
    ap.add_argument("--no-index", action="store_true", help="不重建 文章/README.md")
    ap.add_argument("--no-dedupe", action="store_true", help="不按旧标题+近邻日期去重")
    ap.add_argument("--dedupe-window-days", type=int, default=3)
    args = ap.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})

    links = collect_links(session, args.timeout, args.retries)
    links.sort(key=article_sort_key, reverse=True)
    if args.limit:
        links = links[:args.limit]
    print(f"发现 {len(links)} 个文章链接")

    seen = existing_title_dates(_common.DEFAULT_OUT)
    saved = skipped = failed = 0
    for i, url in enumerate(links, 1):
        try:
            info = parse_article(fetch(session, url, args.timeout, args.retries), url)
            if not args.no_dedupe and not args.overwrite:
                if should_skip_existing(info, seen, args.dedupe_window_days):
                    skipped += 1
                    print(f"[{i}/{len(links)}] 已有近似文章，跳过：{info['date']} {info['title']}", flush=True)
                    continue
            path = _common.write_article_md(
                info["title"],
                info["author"],
                info["date"],
                info["content"],
                source=info["source"],
                overwrite=args.overwrite,
            )
            if path:
                saved += 1
                seen.setdefault(normalize_title(info["title"]), []).append(info["date"])
                print(f"[{i}/{len(links)}] 已保存：{path}", flush=True)
            else:
                skipped += 1
                print(f"[{i}/{len(links)}] 文件已存在，跳过：{info['date']} {info['title']}", flush=True)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"[{i}/{len(links)}] 失败 {url}: {e}", flush=True)
        if i < len(links):
            time.sleep(args.delay)

    print(f"完成：保存 {saved}，跳过 {skipped}，失败 {failed}")
    if not args.no_index:
        n = _common.rebuild_index()
        print(f"索引已重建，共 {n} 篇。")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
