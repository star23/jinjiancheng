#!/usr/bin/env python3
"""检索金渐成历史文章存档。

用法:
    python3 search_articles.py 关键词 [关键词2 ...] [--since YYYY-MM] [--until YYYY-MM] [--context N] [--titles]

示例:
    python3 search_articles.py 稳定币 --since 2025-01
    python3 search_articles.py 英伟达 减仓 --context 60
    python3 search_articles.py 4年周期 --titles

默认在仓库根目录的 `文章/` 文件夹中检索（每篇一个 .md，文件名形如 `YYYY-MM-DD 标题.md`）。
"""
import argparse, os, re, sys

def find_articles_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    # skill/scripts -> skill -> repo root
    for cand in [
        os.path.join(here, "..", "..", "文章"),
        os.path.join(here, "..", "文章"),
        os.path.join(os.getcwd(), "文章"),
    ]:
        cand = os.path.abspath(cand)
        if os.path.isdir(cand):
            return cand
    sys.exit("找不到 文章/ 目录，请在仓库根目录运行，或确认存档已生成。")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keywords", nargs="+", help="一个或多个关键词（AND 匹配，全部命中才算）")
    ap.add_argument("--since", help="起始月份 YYYY-MM")
    ap.add_argument("--until", help="结束月份 YYYY-MM")
    ap.add_argument("--context", type=int, default=40, help="命中片段上下文字符数 (默认 40)")
    ap.add_argument("--titles", action="store_true", help="只列出命中文章的标题")
    args = ap.parse_args()

    d = find_articles_dir()
    files = sorted(f for f in os.listdir(d) if f.endswith(".md") and f != "README.md")
    hits = 0
    for fn in files:
        date = fn[:10]
        ym = date[:7]
        if args.since and ym < args.since: continue
        if args.until and ym > args.until: continue
        text = open(os.path.join(d, fn), encoding="utf-8").read()
        if not all(k in text for k in args.keywords): continue
        hits += 1
        if args.titles:
            print(fn[:-3]); continue
        print(f"\n===== {fn[:-3]} =====")
        kw = args.keywords[0]
        for m in re.finditer(re.escape(kw), text):
            s = max(0, m.start() - args.context); e = min(len(text), m.end() + args.context)
            frag = text[s:e].replace("\n", " ")
            print(f"  …{frag}…")
    if hits == 0:
        print("无命中。")
    else:
        print(f"\n共命中 {hits} 篇。", file=sys.stderr)

if __name__ == "__main__":
    main()
