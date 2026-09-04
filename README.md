# 金渐成（玑哥）内容存档 + Skill

抓取并整理财经博主 **金渐成**（玑哥 / 金不换 / 天玑，微信公众号《金渐成》《天机奇谈》作者，
站点 https://jinjiancheng.com/ ）的公开历史文章，并据此构建一个可复用的 Claude Skill。

## 目录结构

```
.
├── 文章/                      # 历史文章存档（762 篇，每篇一个 .md）
│   ├── README.md              # 文章索引（按时间倒序，含字数）
│   └── YYYY-MM-DD 标题.md
└── jinjiancheng.skill/        # Claude Skill：金渐成投资观点
    ├── SKILL.md               # 技能主文件（含 name/description 元数据、工作流、速查）
    ├── references/            # 分主题观点提炼
    │   ├── 01-投资哲学与方法论.md
    │   ├── 02-宏观环境.md
    │   ├── 03-AI.md
    │   ├── 04-美股.md
    │   ├── 05-BTC.md
    │   └── 06-Crypto.md
    └── scripts/
        ├── search_articles.py # 全文检索工具
        └── articles_index.json# 文章轻量索引（日期/标题/作者/字数）
```

## 1) 历史文章存档（`文章/`）

- **762 篇**，时间跨度 **2020-02-17 → 2026-08-28**，约 **159.5 万字**。
- 每篇为独立 Markdown，含 YAML frontmatter（标题/作者/日期/字数/来源）。
- 索引见 [`文章/README.md`](文章/README.md)。

## 2) Skill（`jinjiancheng.skill/`）

基于全部文章提炼金渐成对 **宏观环境、AI、美股、BTC、Crypto** 的看法、框架与历史预测，
覆盖其方法论（拥抱科技、三账户体系、金字塔加仓、做低成本/负成本、杠铃策略、4 年周期、VIX 择时等）。

**检索文章原文：**
```bash
python3 jinjiancheng.skill/scripts/search_articles.py 稳定币 --since 2025-01
python3 jinjiancheng.skill/scripts/search_articles.py 英伟达 减仓 --context 60
python3 jinjiancheng.skill/scripts/search_articles.py 4年周期 --titles
```

**作为 Claude Code 技能使用：** 将 `jinjiancheng.skill/` 放到技能目录（如 `~/.claude/skills/jinjiancheng/`，
或项目内 `.claude/skills/jinjiancheng/`，目录里需有 `SKILL.md`）即可被自动发现。

## 数据来源与说明

- 文章正文主要抓取自 https://jinjiancheng.com/articles 及其单篇文章页；尚未进入官网存档的文章按公众号原文补录，并保留原始微信链接。
- **时间边界**：当前存档止于 **2026-08-28**。其公众号 2026 年因合规多次被处罚/迁移，作者自述 2026-09-30 新规后
  将不再披露持仓与个股分析；后续内容可通过 `scrapers/scrape_site_static.py` 继续同步。
- 所有内容**仅供研究参考，不构成投资建议**（沿用作者本人口径）。投资有风险，决策需自负。
