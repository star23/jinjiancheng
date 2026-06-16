"""共享工具：文章 Markdown 落盘、文件名清洗、索引重建、HTML 转文本。

被 fetch_wechat_article.py / wechat_rss_sync.py / scrape_site_playwright.py /
scrape_site_static.py 复用。
输出格式与仓库 `文章/` 目录中既有文件保持一致。
"""
from __future__ import annotations
import os, re, html as _html

# 仓库根目录下的文章输出目录
DEFAULT_OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "文章"))


def sanitize_filename(name: str) -> str:
    name = (name or "").replace("/", "／").replace("\\", "＼").replace(":", "：")
    name = re.sub(r'[\x00-\x1f<>:"|?*]', "", name)
    return name.strip()[:80] or "无标题"


def count_words(text: str) -> int:
    return len(re.sub(r"\s", "", text or ""))


def html_to_text(fragment: str) -> str:
    """把微信/网页正文 HTML 粗略转为带段落的纯文本。

    无第三方依赖；保留段落换行，图片转为 Markdown 占位，丢弃脚本/样式。
    若安装了 bs4，调用方可自行替换为更精细的解析。
    """
    if not fragment:
        return ""
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", fragment)
    # 图片 -> markdown（优先 data-src，微信懒加载）
    def img(m):
        tag = m.group(0)
        src = re.search(r'(?:data-src|src)="([^"]+)"', tag)
        return f"\n![]({src.group(1)})\n" if src else "\n"
    h = re.sub(r"(?is)<img[^>]*>", img, h)
    # 块级元素 -> 换行
    h = re.sub(r"(?is)</(p|div|section|br|li|h[1-6]|blockquote)>", "\n", h)
    h = re.sub(r"(?is)<br\s*/?>", "\n", h)
    h = re.sub(r"(?is)<[^>]+>", "", h)          # 去掉剩余标签
    h = _html.unescape(h)
    h = re.sub(r"[ \t 　]+", " ", h)
    h = re.sub(r"\n[ \t]+", "\n", h)
    h = re.sub(r"\n{3,}", "\n\n", h)
    return h.strip()


def write_article_md(title: str, author: str, date: str, content: str,
                     source: str = "https://jinjiancheng.com/",
                     out_dir: str = DEFAULT_OUT, overwrite: bool = False) -> str | None:
    """写入一篇文章，返回写入路径；若已存在且 overwrite=False 则返回 None。"""
    os.makedirs(out_dir, exist_ok=True)
    title = (title or "无标题").strip()
    date = (date or "0000-00-00").strip()[:10]
    content = "\n".join(line.rstrip() for line in (content or "").splitlines()).strip()
    wc = count_words(content)
    fn = f"{date} {sanitize_filename(title)}.md"
    path = os.path.join(out_dir, fn)
    if os.path.exists(path) and not overwrite:
        return None
    esc = title.replace('"', '\\"')
    md = (
        "---\n"
        f'title: "{esc}"\n'
        f'author: "{author or "金渐成"}"\n'
        f'date: "{date}"\n'
        f"word_count: {wc}\n"
        f'source: "{source}"\n'
        "---\n\n"
        f"# {title}\n\n"
        f"> 作者：{author or '金渐成'}　|　发布日期：{date}　|　字数：约{wc}字\n\n"
        f"{content.strip()}\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path


def _read_frontmatter(path: str) -> dict:
    out = {}
    try:
        with open(path, encoding="utf-8") as f:
            txt = f.read()
    except OSError:
        return out
    m = re.match(r"^---\n(.*?)\n---", txt, re.S)
    if not m:
        return out
    for line in m.group(1).splitlines():
        kv = re.match(r'(\w+):\s*"?(.*?)"?\s*$', line)
        if kv:
            out[kv.group(1)] = kv.group(2)
    return out


def rebuild_index(out_dir: str = DEFAULT_OUT) -> int:
    """重建 文章/README.md 索引（按时间倒序）。返回文章数。"""
    rows = []
    for fn in os.listdir(out_dir):
        if not fn.endswith(".md") or fn == "README.md":
            continue
        fm = _read_frontmatter(os.path.join(out_dir, fn))
        rows.append((fm.get("date", fn[:10]), fm.get("title", fn[:-3]),
                     fn, fm.get("word_count", "")))
    rows.sort(reverse=True)
    if not rows:
        return 0
    dmin = min(r[0] for r in rows); dmax = max(r[0] for r in rows)
    lines = [
        "# 金渐成 历史文章存档\n",
        f"\n本目录收录金渐成（玑哥 / 金不换）公众号《金渐成》《天机奇谈》的历史文章，"
        f"共 **{len(rows)}** 篇，时间跨度 **{dmin} ～ {dmax}**。\n",
        "\n> 来源：https://jinjiancheng.com/。\n",
        "\n## 文章列表（按时间倒序）\n",
        "\n| 日期 | 标题 | 字数 |",
        "| --- | --- | --- |",
    ]
    for date, title, fn, wc in rows:
        lines.append(f"| {date} | [{title}](<{fn}>) | {wc} |")
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return len(rows)
