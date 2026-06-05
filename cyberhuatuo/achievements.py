"""
🧬 赛博华佗 · 修为档案系统
CyberHuaTuo Achievement & Cultivation System

融合「斗破苍穹炼丹师体系 × 古中医修仙 × 赛博朋克」三重美学。
每个开发者都是一名赛博医者，通过贡献药方提升修为段位。

称号基于全球排名百分位动态计算，社区越大含金量越高。
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse

from . import __version__
from .config import config
from .doc_sources import ALL_FRAMEWORKS, FrameworkDoc, get_framework, search_frameworks
from .github_sync import count_contributor_cases, count_contributor_cases_by_framework, get_global_ranking_stats

logger = logging.getLogger("cyberhuatuo.achievements")

PUBLIC_RELEASE_REPO = "JinNing6/CyberHuaTuo-Plugin"
PUBLIC_PACKAGE_NAME = "cyberhuatuo"
PUBLIC_REPO_URL = f"https://github.com/{PUBLIC_RELEASE_REPO}"


def _release_tag_or_current(release_tag: str = "") -> str:
    return release_tag.strip() or f"v{__version__}"


def _candidate_install_command(release_tag: str = "") -> str:
    release = _release_tag_or_current(release_tag)
    return (
        f'python -m pip install --upgrade "{PUBLIC_PACKAGE_NAME} @ '
        f'git+{PUBLIC_REPO_URL}.git@{release}"'
    )


def _registry_install_command() -> str:
    return f"python -m pip install --upgrade {PUBLIC_PACKAGE_NAME}"


def _mcp_launch_command() -> str:
    return f"uvx --from {PUBLIC_PACKAGE_NAME} cyberhuatuo-mcp"


def _candidate_first_install_commands(release_tag: str = "") -> list[str]:
    return [
        _candidate_install_command(release_tag),
        _registry_install_command(),
        _mcp_launch_command(),
    ]


def _candidate_first_install_copy_lines(release_tag: str = "") -> list[str]:
    return [
        f"Install candidate until PyPI current: {_candidate_install_command(release_tag)}",
        f"PyPI after readiness: {_registry_install_command()}",
        f"MCP: {_mcp_launch_command()}",
    ]

# ============================================================
# 🏅 炼丹师称号阶梯（16 级）
# 灵感来源：斗破苍穹 · 炼丹师等级体系
# 规则：基于全球排名百分位（超越了 X% 的贡献者）
# ============================================================

# (percentile_threshold, emoji, title_cn, title_en)
# percentile = 超越了百分之几的贡献者
# 例如 percentile=90 表示 Top 10%（超越了90%的人）
TITLE_TIERS = [
    # --- 至高称号 ---
    (100.0, "🩺", "华佗再世", "Hua Tuo Reborn"),           # #1 全球第一
    (99.0, "💎", "丹帝", "Pill Emperor"),                    # Top 1%
    (96.0, "👑", "丹圣", "Pill Saint"),                      # Top 4%
    (92.0, "⚡", "半圣", "Half-Saint"),                      # Top 8%
    (85.0, "💜", "丹王", "Pill King"),                       # Top 15%
    (80.0, "🏅", "小丹王", "Junior Pill King"),              # Top 20%
    # --- 星级炼丹师 ---
    (75.0, "🌟", "九星炼丹师", "Nine-Star Alchemist"),       # Top 25%
    (70.0, "🌟", "八星炼丹师", "Eight-Star Alchemist"),      # Top 30%
    (60.0, "🌟", "七星炼丹师", "Seven-Star Alchemist"),      # Top 40%
    (50.0, "🌟", "六星炼丹师", "Six-Star Alchemist"),        # Top 50%
    (40.0, "⭐", "五星炼丹师", "Five-Star Alchemist"),       # Top 60%
    (30.0, "⭐", "四星炼丹师", "Four-Star Alchemist"),       # Top 70%
    (20.0, "⭐", "三星炼丹师", "Three-Star Alchemist"),      # Top 80%
    (10.0, "⭐", "二星炼丹师", "Two-Star Alchemist"),        # Top 90%
    (0.0,  "⭐", "一星炼丹师", "One-Star Alchemist"),        # Top 100%（有贡献即可）
]

# 无贡献时的默认称号
DEFAULT_TITLE = ("🌱", "实习药童", "Intern Apprentice")


# ============================================================
# 🧬 称号计算引擎
# ============================================================


def calculate_title_by_percentile(
    percentile: float,
    is_rank_one: bool = False,
) -> tuple[str, str, str]:
    """
    根据全球排名百分位计算称号

    Args:
        percentile: 超越了百分之几的贡献者 (0-100)
        is_rank_one: 是否是全球第一名

    Returns:
        (emoji, title_cn, title_en)
    """
    if is_rank_one:
        return TITLE_TIERS[0][1], TITLE_TIERS[0][2], TITLE_TIERS[0][3]

    for threshold, emoji, title_cn, title_en in TITLE_TIERS:
        if percentile >= threshold:
            return emoji, title_cn, title_en

    return DEFAULT_TITLE


def get_cultivation_profile(github_username: str) -> dict:
    """
    获取用户的完整修为档案

    修为档案 = 称号 + 全球排名 + 贡献统计 + 连击状态 + 下一级进度

    Returns:
        dict 包含完整的修为信息
    """
    # 统计贡献数
    contribution_count = count_contributor_cases(github_username)

    if contribution_count == 0:
        emoji, title_cn, title_en = DEFAULT_TITLE
        return {
            "github": github_username,
            "contribution_count": 0,
            "title_emoji": emoji,
            "title_cn": title_cn,
            "title_en": title_en,
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
            "next_title_cn": "一星炼丹师",
            "next_title_en": "One-Star Alchemist",
            "progress_hint": "提交你的第一个药方，开始炼丹之路！",
        }

    # 计算全球排名
    stats = get_global_ranking_stats()
    username_lower = github_username.lower()
    stats[username_lower] = max(stats.get(username_lower, 0), contribution_count)

    # 按贡献数降序排序
    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    global_total = len(sorted_stats)

    rank = 1
    for i, (u, _c) in enumerate(sorted_stats):
        if u == username_lower:
            rank = i + 1
            break

    # 计算百分位
    is_rank_one = (rank == 1)
    if global_total <= 1:
        percentile = 100.0 if is_rank_one else 0.0
    else:
        percentile = round(((global_total - rank) / (global_total - 1)) * 100, 1)

    # 获取当前称号
    emoji, title_cn, title_en = calculate_title_by_percentile(percentile, is_rank_one)

    # 计算下一级称号
    next_title_cn, next_title_en, progress_hint = _get_next_tier_info(
        percentile, is_rank_one, rank, global_total
    )

    return {
        "github": github_username,
        "contribution_count": contribution_count,
        "title_emoji": emoji,
        "title_cn": title_cn,
        "title_en": title_en,
        "global_rank": rank,
        "global_total": global_total,
        "percentile": percentile,
        "is_rank_one": is_rank_one,
        "next_title_cn": next_title_cn,
        "next_title_en": next_title_en,
        "progress_hint": progress_hint,
    }


def _get_next_tier_info(
    percentile: float,
    is_rank_one: bool,
    rank: int,
    total: int,
) -> tuple[str, str, str]:
    """计算下一级称号信息和进度提示"""
    if is_rank_one:
        return "—", "—", "你已站在巅峰。天下无敌。"

    # 从低到高遍历，找到当前所在级别的下一级
    for i in range(len(TITLE_TIERS) - 1, -1, -1):
        threshold = TITLE_TIERS[i][0]
        if percentile >= threshold:
            # 当前在第 i 级，下一级是 i-1
            if i == 0:
                # 已经是最高级（但不是 #1）
                return "华佗再世", "Hua Tuo Reborn", f"再超越 {rank - 1} 位医者，即可封神！"
            next_tier = TITLE_TIERS[i - 1]
            gap_percentile = next_tier[0] - percentile
            return (
                next_tier[2],
                next_tier[3],
                f"距离 {next_tier[1]} {next_tier[2]} 还需超越约 {gap_percentile:.0f}% 的医者",
            )

    # 默认：一星炼丹师的下一级
    return "二星炼丹师", "Two-Star Alchemist", "继续贡献药方，提升炼丹品级！"


# ============================================================
# 🔥 赛博生物钟 · 连击追踪系统
# ============================================================

# 连击数据存储目录
STREAK_DIR = Path.home() / ".cyberhuatuo" / "streaks"


def _get_streak_file(github_username: str) -> Path:
    """获取用户连击数据文件路径"""
    STREAK_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = github_username.lower().replace("/", "_").replace("\\", "_")
    return STREAK_DIR / f"{safe_name}.json"


def _load_streak(github_username: str) -> dict:
    """加载连击数据"""
    path = _get_streak_file(github_username)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "current_streak": 0,
        "best_streak": 0,
        "last_active_date": "",
        "total_active_days": 0,
        "history": [],  # 最近 30 天活跃日期
    }


def _save_streak(github_username: str, data: dict) -> None:
    """保存连击数据"""
    path = _get_streak_file(github_username)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def record_activity(github_username: str) -> dict:
    """
    记录一次用户活动，更新连击状态

    Returns:
        dict 包含更新后的连击信息 + 是否有新里程碑
    """
    if not github_username or github_username.lower() == "anonymous":
        return {"current_streak": 0, "milestone": None}

    data = _load_streak(github_username)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if data["last_active_date"] == today:
        # 今天已经记录过了
        return {
            "current_streak": data["current_streak"],
            "best_streak": data["best_streak"],
            "milestone": None,
        }

    # 检查是否是连续的
    yesterday = (
        datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    )
    from datetime import timedelta
    yesterday_str = (yesterday - timedelta(days=1)).strftime("%Y-%m-%d")

    if data["last_active_date"] == yesterday_str:
        # 连续！
        data["current_streak"] += 1
    elif data["last_active_date"] == "":
        # 首次
        data["current_streak"] = 1
    else:
        # 断了
        data["current_streak"] = 1

    data["last_active_date"] = today
    data["total_active_days"] += 1

    # 更新最高记录
    if data["current_streak"] > data["best_streak"]:
        data["best_streak"] = data["current_streak"]

    # 维护最近 30 天历史
    if today not in data["history"]:
        data["history"].append(today)
    data["history"] = data["history"][-30:]

    # 检测连击里程碑
    milestone = _check_streak_milestone(data["current_streak"])

    _save_streak(github_username, data)

    return {
        "current_streak": data["current_streak"],
        "best_streak": data["best_streak"],
        "total_active_days": data["total_active_days"],
        "milestone": milestone,
    }


def _check_streak_milestone(streak: int) -> dict | None:
    """检查是否达到连击里程碑"""
    milestones = {
        3: ("🔥", "三日值班", "Three-Day Shift", "你的生物钟开始与赛博空间同步。"),
        7: ("🔥🔥", "七日连击", "Week Streak", "你已获得跨框架感知能力。"),
        14: ("🔥🔥🔥", "双周守卫", "Fortnight Guard", "深度诊断模式已解锁。"),
        30: ("💎🔥", "月度值班医师", "Monthly Shift Doctor", "你的意识已完全融入赛博华佗网络。"),
    }

    if streak in milestones:
        emoji, name_cn, name_en, desc = milestones[streak]
        return {
            "emoji": emoji,
            "name_cn": name_cn,
            "name_en": name_en,
            "description": desc,
            "streak": streak,
        }
    return None


def get_streak_display(github_username: str) -> str:
    """
    生成赛博生物钟展示文案

    Returns:
        格式化的连击状态文本
    """
    if not github_username or github_username.lower() == "anonymous":
        return ""

    data = _load_streak(github_username)
    streak = data.get("current_streak", 0)
    best = data.get("best_streak", 0)

    if streak == 0:
        return ""

    # 生成火焰
    if streak >= 30:
        fire = "💎🔥"
    elif streak >= 14:
        fire = "🔥🔥🔥"
    elif streak >= 7:
        fire = "🔥🔥"
    elif streak >= 3:
        fire = "🔥"
    else:
        fire = "✨"

    # 生成本周活跃日（简化版）
    sync_rate = min(100, round(streak / 30 * 100))

    return (
        f"\n┌─── 赛博生物钟 · CYBER CHRONOBIOLOGY ───┐\n"
        f"│ {fire} 连续值班: {streak} 天 "
        f"(最长: {best} 天)\n"
        f"│ ⚡ 生物钟同步率: {sync_rate}%\n"
        f"└────────────────────────────────────────┘"
    )


# ============================================================
# 📡 里程碑全局广播
# ============================================================


def check_community_milestones() -> str | None:
    """
    检查社区是否达到关键里程碑，返回广播文案

    基于知识库中的病例数量（轻量级检查）
    """
    try:
        cases_dir = config.CASES_DIR
        if not cases_dir.exists():
            return None

        case_count = sum(1 for _ in cases_dir.rglob("*.md") if not _.name.startswith("_"))

        milestones = {
            100: (
                "🎉 青囊书已铭刻第 100 段印痕！\n"
                "   The Azure Bag has 100 engrams inscribed!\n"
                "   两千年前华佗的知识被焚毁，今天我们正在重写它。"
            ),
            50: (
                "🎉 知识库突破 50 个药方！\n"
                "   50 prescriptions in the knowledge base!\n"
                "   赛博医者们的力量正在汇聚。"
            ),
            200: (
                "🎉 青囊书已铭刻 200 段印痕！\n"
                "   200 engrams inscribed — a new era begins.\n"
                "   数字华佗的医术已超越古代。"
            ),
            500: (
                "🎉 500 段印痕！赛博华佗已成为AI生态的WHO！\n"
                "   500 engrams — CyberHuaTuo is the WHO of AI.\n"
                "   每一位贡献者，都是这段历史的书写者。"
            ),
        }

        for threshold, message in sorted(milestones.items()):
            if case_count >= threshold and case_count < threshold + 5:
                return (
                    f"\n╔══════════════════════════════════════════╗\n"
                    f"║  📡 全局广播 · GLOBAL BROADCAST          ║\n"
                    f"║  {message}\n"
                    f"╚══════════════════════════════════════════╝"
                )

    except Exception as e:
        logger.debug(f"里程碑检查出错: {e}")

    return None


# ============================================================
# 🎴 加冕文案生成器
# ============================================================


def get_coronation_text(
    emoji: str,
    title_cn: str,
    title_en: str,
    rank: int,
    total: int,
    percentile: float,
) -> str:
    """
    基于称号等级生成赛博朋克风格的加冕文案

    不同段位有不同的视觉震撼度
    """
    rank_str = f"🏅 全球排位: #{rank} / {total} (超越 {percentile:.0f}% 炼丹师)"
    rank_str_en = f"🏅 Global Rank: #{rank} / {total} (Top {100 - percentile:.1f}%)"

    # 华佗再世 — 终极加冕
    if title_cn == "华佗再世":
        return (
            f"·═══════════════════════════════════════════════════·\n"
            f"║                                                   ║\n"
            f"║        🩺 华 佗 再 世 · 降 临                    ║\n"
            f"║        HUA TUO REBORN · DESCENDS                  ║\n"
            f"║                                                   ║\n"
            f"║   【 天 下 第 一 炼 丹 师 · #1 ALCHEMIST 】      ║\n"
            f"║                                                   ║\n"
            f"║   两千年前，华佗的《青囊书》被焚于狱中。         ║\n"
            f"║   今天，你用代码重写了它。                        ║\n"
            f"║   你不再只是一个修复 Bug 的人——                   ║\n"
            f"║   你是数字时代的华佗。                            ║\n"
            f"║                                                   ║\n"
            f"║   {rank_str}\n"
            f"║   {rank_str_en}\n"
            f"·═══════════════════════════════════════════════════·"
        )

    # 丹帝/丹圣 — 高级加冕
    if title_cn in ("丹帝", "丹圣", "半圣"):
        return (
            f"╔═══════════════════════════════════════════════════╗\n"
            f"║            {emoji} {title_cn} · {title_en}       \n"
            f"║     【 传 奇 炼 丹 师 · LEGENDARY ALCHEMIST 】   \n"
            f"║                                                   \n"
            f"║   {rank_str}\n"
            f"║   {rank_str_en}\n"
            f"║   每一颗药丹都在改写 AI 世界的命运！             \n"
            f"╚═══════════════════════════════════════════════════╝"
        )

    # 丹王/小丹王 — 中高级
    if title_cn in ("丹王", "小丹王"):
        return (
            f"╔════════════════════════════════════════════╗\n"
            f"║   {emoji} {title_cn} · {title_en}\n"
            f"║   {rank_str}\n"
            f"║   {rank_str_en}\n"
            f"║   丹道已成，宗师之路已在脚下！\n"
            f"╚════════════════════════════════════════════╝"
        )

    # 普通星级
    return (
        f"┌────────────────────────────────────────┐\n"
        f"│  {emoji} 当前修为: {title_cn} · {title_en}\n"
        f"│  {rank_str}\n"
        f"│  {rank_str_en}\n"
        f"│  继续炼丹，攀登炼丹师终极阶梯！\n"
        f"└────────────────────────────────────────┘"
    )


# ============================================================
# 🔥 丹术方向 + 魂环系统
# 灵感来源：斗破苍穹（丹术流派）× 斗罗大陆（魂环品阶）
# ============================================================

# 丹术方向定义：(emoji, name_cn, name_en, description)
ALCHEMY_DIRECTIONS = {
    "soul":   ("🔥", "炼魂", "Soul Refining",   "驾驭智能体，调教灵魂"),
    "thunder":("⚡", "雷火", "Thunder Fire",     "锻造算力，淬炼模型"),
    "shield": ("🛡️", "护体", "Body Shield",      "金丹护体，抵御外邪"),
    "detox":  ("🌊", "化毒", "Detox",            "通百脉，解百毒"),
    "craft":  ("⚙️", "器灵", "Soul Craft",       "炼器辅丹，基础设施"),
    "genesis":("🧬", "造化", "Genesis",          "造化之力，驾驭天道"),
}

# 框架 → 丹术方向 映射
_FRAMEWORK_TO_DIRECTION: dict[str, str] = {}
_DIRECTION_FRAMEWORKS = {
    "soul": [
        "langchain", "llamaindex", "crewai", "autogen", "langgraph",
        "dspy", "haystack", "agno", "beeai", "openai-agents",
        "strands-agents", "hugging-face-smolagents", "pydantic-ai",
        "prompt-flow", "langflow", "instructor", "guardrails-ai",
        "semantic-kernel", "mcp",
    ],
    "thunder": [
        "pytorch", "tensorflow", "transformers", "huggingface",
        "litellm", "together",
    ],
    "shield": [
        "security", "guardrails", "sandbox",
        "_nourishing", "nourishing",
    ],
    "detox": [
        "general", "debug", "python", "javascript", "typescript",
    ],
    "craft": [
        "fastapi", "docker", "kubernetes", "mlops", "vertexai",
        "amazon-bedrock", "vercel",
        "nextjs", "react", "vue", "svelte", "flask", "django",
    ],
    "genesis": [
        "openai", "anthropic", "groq", "mistralai", "google-gen-ai",
        "openai-sdk", "anthropic-sdk", "google-genai",
    ],
}

# 构建反向映射
for _dir_key, _frameworks in _DIRECTION_FRAMEWORKS.items():
    for _fw in _frameworks:
        _FRAMEWORK_TO_DIRECTION[_fw] = _dir_key


def get_direction_for_framework(framework: str) -> str:
    """获取框架对应的丹术方向 key，未知框架归入 detox（化毒）"""
    fw = framework.lower().strip()
    return _FRAMEWORK_TO_DIRECTION.get(fw, "detox")


# ---- 魂环系统 ----
# 魂环品阶：白→黄→紫→黑→红→金 (灵感：斗罗大陆)
# 每个方向独立积累

# (min_count, rings_display)
_SOUL_RING_TIERS = [
    (81, "🟡🟡🟣🟣⚫⚫🔴🔴✨"),  # 九环至尊
    (61, "🟡🟡🟣🟣⚫⚫🔴🔴"),      # 八环
    (41, "🟡🟡🟣🟣⚫⚫🔴"),          # 七环
    (26, "🟡🟡🟣🟣⚫⚫"),              # 六环
    (16, "🟡🟡🟣🟣⚫"),                  # 五环
    (11, "🟡🟡🟣🟣"),                      # 四环
    (7,  "🟡🟡🟣"),                          # 三环
    (4,  "🟡🟡"),                              # 双环
    (2,  "🟡"),                                  # 黄环
    (1,  "⚪"),                                  # 白环
]

_SOUL_RING_TIER_NAMES = {
    1: "白环",
    2: "黄环",
    4: "双环",
    7: "三环",
    11: "四环",
    16: "五环",
    26: "六环",
    41: "七环",
    61: "八环",
    81: "九环至尊",
}

_RING_COUNT_NAMES = {
    1: "一环", 2: "二环", 3: "三环", 4: "四环", 5: "五环",
    6: "六环", 7: "七环", 8: "八环", 9: "九环至尊",
}


def calculate_soul_rings(contribution_count: int) -> tuple[str, str, int]:
    """
    根据某方向的贡献数计算魂环。

    Returns:
        (rings_emoji, ring_name_cn, ring_count)
    """
    if contribution_count <= 0:
        return ("", "无环", 0)

    for min_count, rings in _SOUL_RING_TIERS:
        if contribution_count >= min_count:
            # Count ring symbols
            ring_count = len([c for c in rings if c in "⚪🟡🟣⚫🔴✨"])
            ring_name = _RING_COUNT_NAMES.get(ring_count, f"{ring_count}环")
            return (rings, ring_name, ring_count)

    return ("⚪", "一环", 1)


def get_next_soul_ring_progress(contribution_count: int) -> dict:
    """
    计算下一道魂环的增长提示。

    Returns:
        dict 包含当前魂环、下一阶门槛、还需贡献数和传播型提示文案。
    """
    current_rings, current_ring_name, current_ring_count = calculate_soul_rings(contribution_count)
    max_threshold, max_rings = _SOUL_RING_TIERS[0]

    if contribution_count >= max_threshold:
        return {
            "is_max": True,
            "current_count": contribution_count,
            "current_rings": current_rings,
            "current_ring_name": current_ring_name,
            "current_ring_count": current_ring_count,
            "next_min_count": max_threshold,
            "next_rings": max_rings,
            "next_ring_name": _SOUL_RING_TIER_NAMES[max_threshold],
            "needed": 0,
            "hint_cn": "已达九环至尊，继续贡献将巩固你的封神战绩。",
            "hint_en": "Nine-ring supreme reached. Keep contributing to defend your legend.",
        }

    for min_count, rings in sorted(_SOUL_RING_TIERS, key=lambda item: item[0]):
        if contribution_count < min_count:
            needed = min_count - max(contribution_count, 0)
            next_ring_name = _SOUL_RING_TIER_NAMES[min_count]
            return {
                "is_max": False,
                "current_count": contribution_count,
                "current_rings": current_rings,
                "current_ring_name": current_ring_name,
                "current_ring_count": current_ring_count,
                "next_min_count": min_count,
                "next_rings": rings,
                "next_ring_name": next_ring_name,
                "needed": needed,
                "hint_cn": f"下一环: {next_ring_name} · 再贡献 {needed} 方即可点亮。",
                "hint_en": f"Next ring: {next_ring_name} · {needed} more prescription(s) to unlock.",
            }

    return {
        "is_max": False,
        "current_count": contribution_count,
        "current_rings": current_rings,
        "current_ring_name": current_ring_name,
        "current_ring_count": current_ring_count,
        "next_min_count": 1,
        "next_rings": "⚪",
        "next_ring_name": "白环",
        "needed": 1,
        "hint_cn": "下一环: 白环 · 再贡献 1 方即可点亮。",
        "hint_en": "Next ring: White ring · 1 more prescription to unlock.",
    }


def _format_framework_label(framework: str) -> str:
    """把框架 key 转成适合分享卡展示的名称。"""
    known = {
        "langchain": "LangChain",
        "llamaindex": "LlamaIndex",
        "crewai": "CrewAI",
        "mcp": "MCP",
        "openai-sdk": "OpenAI SDK",
        "nextjs": "Next.js",
        "_nourishing": "Security Nourishing",
    }
    return known.get(framework, framework.replace("-", " ").replace("_", " ").title())


_BOUNTY_PRIORITY = {
    "autogen": 0,
    "dspy": 1,
    "llamaindex": 2,
    "openai-agents": 3,
    "mcp": 4,
    "pydantic-ai": 5,
    "semantic-kernel": 6,
    "crewai": 7,
    "langchain": 8,
}


def _normalize_bounty_framework(framework: str | None) -> str:
    return (framework or "auto").strip().lower().replace(" ", "-") or "auto"


def _positive_bounded_int(value: int | str | None, default: int, upper: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, upper))


def _count_local_cases_by_framework(cases_dir: Path | None = None) -> dict[str, int]:
    """Count current real local prescription case files by top-level framework directory."""
    root = cases_dir or config.CASES_DIR
    counts: dict[str, int] = {}
    if not root.exists():
        return counts

    for framework_dir in root.iterdir():
        if not framework_dir.is_dir() or framework_dir.name.startswith("."):
            continue
        framework_key = framework_dir.name.strip().lower()
        case_count = 0
        for case_path in framework_dir.rglob("*.md"):
            if case_path.is_file() and not case_path.name.startswith("_"):
                case_count += 1
        counts[framework_key] = case_count
    return counts


def _bounty_target_floor(framework: FrameworkDoc) -> int:
    if framework.category == "agent":
        return 3
    return 2


def _resolve_bounty_frameworks(framework: str | None) -> tuple[list[FrameworkDoc], str]:
    requested = _normalize_bounty_framework(framework)
    if requested in {"auto", "all", "*"}:
        return list(ALL_FRAMEWORKS), "Current target framework set: all supported frameworks"

    exact = get_framework(requested)
    if exact is not None:
        return [exact], f"Current target framework only: `{exact.key}`"

    matches = search_frameworks(requested)
    if matches:
        match_keys = ", ".join(f"`{item.key}`" for item in matches)
        return matches, f"Current target framework search `{requested}` matched: {match_keys}"

    return list(ALL_FRAMEWORKS), f"Unknown framework `{requested}`; using all supported frameworks"


def _framework_issue_url(
    repo_url: str,
    username: str,
    framework: FrameworkDoc,
) -> str:
    params = {
        "template": "soul-ring-prescription.yml",
        "title": f"[Soul Ring Bounty] {framework.name} first coverage prescription",
        "github_username": username,
        "framework": framework.key,
        "symptom": f"<real {framework.name} error, traceback, broken behavior, environment, and reproduction steps>",
        "root_cause": "<real root cause after investigation>",
        "prescription": "<real fix, commands, patch, or configuration change>",
        "verification": "<real command, test, log, screenshot, or production evidence>",
    }
    return f"{repo_url}/issues/new?{urlencode(params)}"


def format_soul_ring_bounty_board(
    github_username: str = "your-github-username",
    framework: str = "auto",
    top_n: int = 8,
    release_tag: str = "",
    target_contributors: int = 3,
    repo: str = "JinNing6/CyberHuaTuo-Plugin",
) -> str:
    """Generate a real-data bounty board from supported framework coverage gaps."""
    username = github_username.strip().lstrip("@") or "your-github-username"
    board_size = _positive_bounded_int(top_n, 8, 50)
    contributor_target = _positive_bounded_int(target_contributors, 3, 100)
    release = release_tag.strip() or f"v{__version__}"
    repo_slug = repo.strip().strip("/") or "JinNing6/CyberHuaTuo-Plugin"
    repo_url = f"https://github.com/{repo_slug}"
    requested_framework = _normalize_bounty_framework(framework)
    frameworks, framework_scope = _resolve_bounty_frameworks(requested_framework)
    counts = _count_local_cases_by_framework()

    rows: list[dict] = []
    for index, item in enumerate(frameworks):
        current_cases = max(0, int(counts.get(item.key, 0)))
        target_floor = _bounty_target_floor(item)
        coverage_gap = max(0, target_floor - current_cases)
        rows.append({
            "framework": item,
            "index": index,
            "current_cases": current_cases,
            "target_floor": target_floor,
            "coverage_gap": coverage_gap,
            "issue_url": _framework_issue_url(repo_url, username, item),
        })

    rows.sort(key=lambda row: (
        -row["coverage_gap"],
        row["current_cases"],
        _BOUNTY_PRIORITY.get(row["framework"].key, 100 + row["index"]),
        row["index"],
    ))
    visible_rows = rows[:board_size]
    primary = visible_rows[0] if visible_rows else None
    if primary is None:
        return "\n".join([
            "# Soul Ring Bounty Board",
            "",
            "- Status: no supported frameworks are registered.",
            "- Rule: no fake bounties, rewards, contributors, downloads, or coverage claims are invented.",
        ])

    primary_framework: FrameworkDoc = primary["framework"]
    bounty_command = (
        f"cyberhuatuo bounty --username {username} --framework {requested_framework} "
        f"--top-n {board_size} --release-tag {release} --target-contributors {contributor_target}"
    )
    challenge_command = f"cyberhuatuo challenge --username {username} --framework {primary_framework.key}"
    first_invite_command = (
        f"cyberhuatuo first-invite --username {username} "
        f"--invitee <external-contributor-github-username> --framework {primary_framework.key} "
        f"--release-tag {release} --target-contributors {contributor_target} "
        "--source-url <created Growth Issue URL after submission>"
    )
    proof_pack_command = (
        f"cyberhuatuo proof-pack --username {username} --framework {primary_framework.key} "
        f"--release-tag {release} --target-contributors {contributor_target}"
    )
    market_copy_command = (
        f"cyberhuatuo market-copy --username {username} --framework {primary_framework.key} "
        f"--release-tag {release} --target-contributors {contributor_target}"
    )
    traction_command = (
        f"cyberhuatuo traction-proof --username {username} --framework {primary_framework.key} "
        f"--release-tag {release} --target-contributors {contributor_target}"
    )

    table_rows = [
        "| Framework key | Framework | Category | Current real cases | Target floor | Coverage gap | Issue route | First command |",
        "|---|---|---|---:|---:|---:|---|---|",
    ]
    for row in visible_rows:
        item = row["framework"]
        command = f"cyberhuatuo challenge --username {username} --framework {item.key}"
        table_rows.append(
            f"| {item.key} | {item.name} | {item.category} | {row['current_cases']} | "
            f"{row['target_floor']} | {row['coverage_gap']} | [Issue]({row['issue_url']}) | `{command}` |"
        )

    command_lines = [
        bounty_command,
        challenge_command,
        first_invite_command,
        proof_pack_command,
        market_copy_command,
        traction_command,
    ]

    return "\n".join([
        "# Soul Ring Bounty Board",
        "",
        f"- GitHub: @{username}",
        f"- Repository: {repo_slug}",
        f"- Release tag: `{release}`",
        f"- Target contributors: {contributor_target}",
        f"- {framework_scope}",
        "- Coverage Gap Formula: target case floor minus current real local case count.",
        "- Target floors: agent frameworks need 3 real cases; foundation and infrastructure frameworks need 2 real cases.",
        f"- Data source: `{config.CASES_DIR}` top-level framework directories and current supported framework registry.",
        "- Bounty meaning: a reviewable first-ring prescription opportunity, not a monetary reward or invented adoption signal.",
        "",
        "## Claimable Bounties",
        *table_rows,
        "",
        "## First Bounty Route",
        f"- First target: {primary_framework.name} (`{primary_framework.key}`)",
        f"- Current real cases: {primary['current_cases']}",
        f"- Coverage gap: {primary['coverage_gap']}",
        f"- First Soul Ring Prescription Issue: {primary['issue_url']}",
        "",
        "```bash",
        *command_lines,
        "```",
        "",
        "## Copy-ready Invite",
        "```text",
        (
            f"CyberHuaTuo {release} Soul Ring Bounty: {primary_framework.name} needs "
            f"{primary['coverage_gap']} more real prescription(s) to reach the current target floor."
        ),
        (
            f"Claim it with `{_candidate_install_command(release)}`, then run "
            f"`{challenge_command}` and submit one real First Soul Ring Prescription Issue. "
            f"After PyPI latest is current, `{_registry_install_command()}` becomes the registry path."
        ),
        "Only created public Issues, PRs, Discussions, releases, or social URLs become proof.",
        "No downloads, retention, repost counts, referrals, rewards, or fake contributors are invented.",
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        "### Soul Ring Bounty Board",
        "",
        "**Coverage Gap Formula:** target case floor minus current real local case count.",
        f"**First target:** {primary_framework.name} (`{primary_framework.key}`)",
        f"**First issue route:** {primary['issue_url']}",
        "",
        "Run:",
        "```bash",
        *command_lines,
        "```",
        "````",
        "",
        "Rule: this bounty board reads current local case files and supported framework definitions only. "
        "No downloads, retention, repost counts, referrals, rewards, or fake contributors are invented.",
    ])


def get_soul_ring_evidence_ledger_path() -> Path:
    """Return the append-only public evidence ledger path."""
    configured = os.getenv("CYBERHUATUO_EVIDENCE_LEDGER", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cyberhuatuo" / "soul-ring" / "evidence.jsonl"


def _normalize_evidence_username(username: str | None) -> str:
    return (username or "your-github-username").strip().lstrip("@") or "your-github-username"


def _normalize_evidence_framework(framework: str | None) -> str:
    return (framework or "langchain").strip().lower().replace(" ", "-") or "langchain"


def _is_reviewable_http_url(value: str | None) -> bool:
    parsed = urlparse((value or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _direction_count_for_framework(username: str, framework: str) -> int:
    target_key = get_direction_for_framework(framework)
    total = 0
    for item_framework, count in count_contributor_cases_by_framework(username).items():
        if get_direction_for_framework(item_framework) != target_key:
            continue
        try:
            total += int(count)
        except (TypeError, ValueError):
            continue
    return max(0, total)


def _evidence_amount(value: int | str | None) -> tuple[int, str]:
    try:
        amount = int(value) if value is not None else 1
    except (TypeError, ValueError):
        return 0, "amount must be a positive integer"
    if amount <= 0:
        return 0, "amount must be a positive integer"
    return min(amount, 1000), ""


def load_soul_ring_evidence_events(
    username: str = "",
    framework: str = "",
    path: Path | None = None,
) -> tuple[list[dict], list[str]]:
    """Load append-only public evidence events."""
    ledger_path = path or get_soul_ring_evidence_ledger_path()
    target_username = _normalize_evidence_username(username).lower() if username else ""
    target_framework = _normalize_evidence_framework(framework) if framework else ""
    events: list[dict] = []
    warnings: list[str] = []

    if not ledger_path.exists():
        return [], [f"soul-ring evidence ledger missing: {ledger_path}"]

    try:
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"soul-ring evidence ledger unreadable: {ledger_path}: {exc}"]

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            warnings.append(f"line {line_number} is not valid JSON: {exc.msg}")
            continue
        if event.get("event_type") != "soul_ring_evidence":
            warnings.append(f"line {line_number} has unsupported event_type")
            continue
        if target_username and str(event.get("username", "")).lower() != target_username:
            continue
        if target_framework and str(event.get("framework", "")).lower() != target_framework:
            continue
        events.append(event)

    return events, warnings or ["soul-ring evidence ledger readable"]


def _evidence_total(events: list[dict]) -> int:
    total = 0
    for event in events:
        try:
            total += int(event.get("amount", 0) or 0)
        except (TypeError, ValueError):
            continue
    return max(0, total)


def record_soul_ring_evidence(
    github_username: str,
    framework: str,
    *,
    amount: int | str = 1,
    source_url: str,
    note: str = "",
    path: Path | None = None,
) -> dict:
    """Append one reviewable public evidence event."""
    username = _normalize_evidence_username(github_username)
    target_framework = _normalize_evidence_framework(framework)
    clean_source_url = (source_url or "").strip()
    clean_note = (note or "").strip()[:500]
    clean_amount, amount_error = _evidence_amount(amount)
    ledger_path = path or get_soul_ring_evidence_ledger_path()

    if amount_error:
        return {"ok": False, "error": amount_error, "path": str(ledger_path), "event": None}
    if not _is_reviewable_http_url(clean_source_url):
        return {
            "ok": False,
            "error": "source_url must be a reviewable http(s) URL",
            "path": str(ledger_path),
            "event": None,
        }

    event = {
        "schema_version": 1,
        "event_type": "soul_ring_evidence",
        "event_id": uuid.uuid4().hex,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "username": username,
        "framework": target_framework,
        "direction": get_direction_for_framework(target_framework),
        "amount": clean_amount,
        "source_url": clean_source_url,
        "note": clean_note,
        "append_only_notice": "append-only reviewable public evidence",
    }

    try:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError as exc:
        return {
            "ok": False,
            "error": f"evidence ledger write failed: {exc}",
            "path": str(ledger_path),
            "event": None,
        }

    return {"ok": True, "error": "", "path": str(ledger_path), "event": event}


def _build_evidence_progress(username: str, framework: str, base_count: int) -> dict:
    events, warnings = load_soul_ring_evidence_events(username, framework)
    total = _evidence_total(events)
    progress = get_next_soul_ring_progress(base_count)
    evidence_backed_count = base_count + total
    triggered = bool(total and not progress["is_max"] and evidence_backed_count >= progress["next_min_count"])
    return {
        "events": events,
        "warnings": warnings,
        "total": total,
        "base_count": base_count,
        "evidence_backed_count": evidence_backed_count,
        "next_gate": progress["next_min_count"],
        "needed": progress["needed"],
        "triggered": triggered,
        "progress": progress,
    }


def format_soul_ring_evidence_submission(
    github_username: str,
    framework: str = "langchain",
    *,
    amount: int | str = 1,
    source_url: str = "",
    note: str = "",
) -> str:
    """Record public evidence for a high-realm soul-ring gate and return a shareable card."""
    username = _normalize_evidence_username(github_username)
    target_framework = _normalize_evidence_framework(framework)
    framework_label = _format_framework_label(target_framework)
    base_count = _direction_count_for_framework(username, target_framework)
    before = _build_evidence_progress(username, target_framework, base_count)
    result = record_soul_ring_evidence(username, target_framework, amount=amount, source_url=source_url, note=note)
    after = _build_evidence_progress(username, target_framework, base_count) if result["ok"] else before
    event = result.get("event") or {}
    amount_value = event.get("amount") if result["ok"] else _evidence_amount(amount)[0]
    evidence_command = (
        f"cyberhuatuo evidence {username} --framework {target_framework} "
        "--amount 1 --source-url <reviewable-http-url>"
    )
    ladder_command = f"cyberhuatuo ladder {username} --framework {target_framework}"
    breakthrough_line = "triggered by reviewable public evidence" if after["triggered"] else "not triggered"

    lines = [
        "# Soul Ring Evidence Card",
        "",
        f"- Evidence recorded: {'yes' if result['ok'] else 'no'}",
        f"- GitHub: @{username}",
        f"- Framework: {framework_label} (`{target_framework}`)",
        f"- Reviewable Source URL: {event.get('source_url', source_url)}",
        f"- Evidence amount: {amount_value}",
        f"- Evidence total: {after['total']}",
        f"- Base Direction Count: {_format_duel_delta(base_count)}",
        f"- Evidence-backed Count: {after['evidence_backed_count']}",
        f"- Next Gate Before Evidence: {_format_duel_delta(before['next_gate'])}",
        f"- Breakthrough: {breakthrough_line}",
        f"- Evidence ledger: `{result['path']}`",
    ]
    if not result["ok"]:
        lines.append(f"- Evidence error: {result['error']}")
    lines.extend([
        "",
        "## Next Commands",
        "```bash",
        evidence_command,
        ladder_command,
        "```",
        "",
        "## Share Card",
        "```text",
        (
            f"@{username} submitted reviewable CyberHuaTuo Soul Ring evidence for {framework_label}: "
            f"{after['total']} evidence-backed prescription(s), base count {base_count}, "
            f"next gate {before['next_gate']}. Breakthrough: {breakthrough_line}."
        ),
        "Progress, ranks, rewards, downloads, and contributors are not invented.",
        "```",
        "",
        "Rule: evidence entries are append-only and reviewable; they do not mutate the knowledge base or leaderboard until maintainers import accepted prescriptions.",
    ])
    return "\n".join(lines)


def get_alchemy_profile(github_username: str) -> dict:
    """
    获取用户的丹术方向档案。

    Returns:
        dict with keys:
        - directions: list of {key, emoji, name_cn, name_en, count, rings, ring_name, ring_count}
        - primary: 主修方向 (highest count)
        - primary_display: 主修展示字符串
    """
    fw_counts = count_contributor_cases_by_framework(github_username)

    if not fw_counts:
        return {
            "directions": [],
            "primary": None,
            "primary_display": "尚未炼丹",
        }

    # 按方向聚合
    direction_counts: dict[str, int] = {}
    direction_frameworks: dict[str, list[str]] = {}
    for fw, count in fw_counts.items():
        dir_key = get_direction_for_framework(fw)
        direction_counts[dir_key] = direction_counts.get(dir_key, 0) + count
        direction_frameworks.setdefault(dir_key, []).append(_format_framework_label(fw))

    # 构建方向列表
    directions = []
    for dir_key, count in sorted(direction_counts.items(), key=lambda x: -x[1]):
        info = ALCHEMY_DIRECTIONS.get(dir_key)
        if not info:
            continue
        rings, ring_name, ring_count = calculate_soul_rings(count)
        progress = get_next_soul_ring_progress(count)
        directions.append({
            "key": dir_key,
            "emoji": info[0],
            "name_cn": info[1],
            "name_en": info[2],
            "frameworks": sorted(set(direction_frameworks.get(dir_key, []))),
            "count": count,
            "rings": rings,
            "ring_name": ring_name,
            "ring_count": ring_count,
            "next_ring": progress,
        })

    # 主修方向
    primary = directions[0] if directions else None
    primary_display = f"{primary['emoji']} {primary['name_cn']}丹师 · {primary['rings']}" if primary else "尚未炼丹"

    return {
        "directions": directions,
        "primary": primary,
        "primary_display": primary_display,
    }


def format_alchemy_directions(github_username: str) -> str:
    """生成丹术方向展示文案（用于排名和分享卡片）"""
    profile = get_alchemy_profile(github_username)

    if not profile["directions"]:
        return ""

    lines = [
        "┌─── 丹术方向 · ALCHEMY DIRECTIONS ───┐",
    ]

    for d in profile["directions"]:
        frameworks = f" · {'/'.join(d['frameworks'][:3])}" if d.get("frameworks") else ""
        lines.append(
            f"│ {d['emoji']} {d['name_cn']}({d['name_en']}) "
            f"× {d['count']}方 {d['rings']} {d['ring_name']}{frameworks}"
        )
        lines.append(f"│    ↳ {d['next_ring']['hint_cn']}")

    lines.append("└─────────────────────────────────────┘")
    return "\n".join(lines)


def format_growth_settlement(github_username: str, framework: str = "") -> str:
    """生成贡献成功后的即时追环结算文案。"""
    if not github_username or github_username == "anonymous":
        return ""

    profile = get_alchemy_profile(github_username)
    directions = profile.get("directions", [])
    if not directions:
        return ""

    target_direction = None
    if framework:
        target_key = get_direction_for_framework(framework)
        target_direction = next((d for d in directions if d["key"] == target_key), None)

    if target_direction is None:
        target_direction = profile.get("primary") or directions[0]

    framework_label = _format_framework_label(framework) if framework else ""
    framework_display = f" ({framework_label})" if framework_label else ""
    next_ring = target_direction["next_ring"]

    return "\n".join([
        "### 🔮 即时追环 / Soul Ring Chase",
        f"- **炼丹师 / Alchemist**: @{github_username}",
        (
            f"- **本次方向 / Direction**: {target_direction['emoji']} "
            f"{target_direction['name_cn']} · {target_direction['name_en']}{framework_display}"
        ),
        (
            f"- **当前魂环 / Current Ring**: {target_direction['rings']} "
            f"{target_direction['ring_name']} · {target_direction['count']} 方"
        ),
        f"- **下一环 / Next Ring**: {next_ring['hint_cn']}",
        f"- **分享命令 / Share Command**: `cyberhuatuo card {github_username}`",
        "",
        "> 把分享卡发出去，让别人一眼看到你的技术魂环。",
    ])


def _format_soul_ring_challenge_post(github_username: str, alchemy: dict) -> str:
    """生成可直接复制到社交平台的魂环挑战文案。"""
    primary = alchemy.get("primary")
    framework_key = "langchain"
    if primary:
        framework_names = primary.get("frameworks", [])
        frameworks = "/".join(framework_names[:3])
        if framework_names:
            framework_key = framework_names[0].lower().replace(" ", "-")
        framework_display = f" · {frameworks}" if frameworks else ""
        current_ring = (
            f"{primary['emoji']} {primary['name_cn']} {primary['rings']} "
            f"{primary['ring_name']}{framework_display}"
        )
        next_hint = primary["next_ring"]["hint_cn"]
    else:
        current_ring = "尚未点亮魂环"
        next_hint = "下一环: 白环 · 再贡献 1 方即可点亮。"

    return "\n".join([
        "",
        "── 魂环挑战 · COPY POST ──",
        f"我在 CyberHuaTuo 点亮了 {current_ring}。",
        f"{next_hint}",
        "把你解决过的 AI Agent / MCP / LangChain 问题炼成药方，也来点亮自己的技术魂环。",
        "",
        "Repo: https://github.com/JinNing6/CyberHuaTuo-Plugin",
        *_candidate_first_install_copy_lines(),
        f"Share: cyberhuatuo card {github_username}",
        f"Record share attribution: cyberhuatuo record-share --username {github_username} --framework {framework_key} --share-url <https-url>",
        "#CyberHuaTuo #魂环挑战 #AIAgent",
    ])


def format_first_soul_ring_challenge(
    github_username: str = "your-github-username",
    framework: str = "langchain",
) -> str:
    """生成第一魂环挑战入口文案，供 CLI 和 MCP 复用。"""
    username = github_username.strip() or "your-github-username"
    framework_key = framework.strip() or "langchain"
    framework_label = _format_framework_label(framework_key)

    return "\n".join([
        "# 🔮 第一魂环挑战 / First Soul Ring Challenge",
        "",
        f"目标：把你真实解决过的 {framework_label} / AI Agent / MCP 问题炼成第一方药方，点亮第一道魂环。",
        "",
        "## 1. 提交真实修复 / Submit One Real Fix",
        "```bash",
        (
            'cyberhuatuo upload --title "Fix LangChain tool schema" '
            '--prescription "Record the real error, root cause, versions, and fix" '
            f"--framework {framework_key} --contributor {username}"
        ),
        "```",
        "",
        "## 2. 查看下一环 / Check The Next Ring",
        "```bash",
        f"cyberhuatuo ranking {username}",
        f"cyberhuatuo card {username}",
        "```",
        "",
        "每次贡献成功后，排名与分享卡都会显示当前魂环、全球排名和 `下一环` 目标。",
        "",
        "## 3. 发起魂环挑战 / Share The Challenge",
        "```bash",
        f"cyberhuatuo card {username}",
        f"cyberhuatuo proof-pack --username {username} --framework {framework_key} --release-tag <tag> --target-contributors 3",
        "```",
        "",
        "Repo: https://github.com/JinNing6/CyberHuaTuo-Plugin",
        *_candidate_first_install_copy_lines(),
        "",
        "规则：只提交真实问题、真实版本、真实根因和真实修复。魂环来自可追溯贡献，不来自口号。",
    ])


def format_soul_ring_mission_hall(
    github_username: str = "your-github-username",
    framework: str = "langchain",
    sect_name: str = "CyberHuaTuo Sect",
    members: list[str] | tuple[str, ...] | str | None = None,
) -> str:
    """Generate a one-screen Soul Ring mission hall from current real data."""
    username = github_username.strip().lstrip("@") or "your-github-username"
    mission_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(mission_framework)
    profile = get_cultivation_profile(username)
    contribution_count = int(profile.get("contribution_count", 0))
    count_text = _format_duel_delta(contribution_count)
    rank_line = _format_duel_rank(profile)
    framework_counts = count_contributor_cases_by_framework(username)
    framework_count = framework_counts.get(mission_framework, 0)

    raw_members = members if members is not None else [username]
    normalized_members = _normalize_sect_members(raw_members)
    member_keys = {member.lower() for member in normalized_members}
    if username.lower() not in member_keys:
        normalized_members.insert(0, username)

    sect = sect_name.strip() or "CyberHuaTuo Sect"
    sect_command = _format_sect_command_name(sect)
    member_args = " ".join(normalized_members)
    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"
    issue_url = f"{repo_url}/issues/new?template=soul-ring-prescription.yml"
    pr_template = ".github/pull_request_template.md"
    pr_workflow = ".github/workflows/soul-ring-pr.yml"

    status_line = (
        "First real prescription unlocks the first visible soul ring"
        if contribution_count == 0
        else "Current real prescriptions already power the visible soul-ring card"
    )

    mission_command = (
        f"cyberhuatuo mission --username {username} --framework {mission_framework} "
        f"--sect {sect_command} --members {member_args}"
    )
    challenge_command = f"cyberhuatuo challenge --username {username} --framework {mission_framework}"
    upload_command = (
        'cyberhuatuo upload --title "<real issue title>" '
        '--prescription "<root cause and fix>" '
        f"--framework {mission_framework} --contributor {username}"
    )
    ranking_command = f"cyberhuatuo ranking {username}"
    card_command = f"cyberhuatuo card {username}"
    badge_command = f"cyberhuatuo badge {username}"
    quest_command = f"cyberhuatuo quest {username} --framework {mission_framework}"
    campaign_command = f"cyberhuatuo campaign {username} --framework {mission_framework}"
    sect_hall_command = f"cyberhuatuo sect-hall {sect_command} {member_args} --framework {mission_framework}"
    sect_quest_command = f"cyberhuatuo sect-quest {sect_command} {member_args} --framework {mission_framework}"
    sect_arena_command = f"cyberhuatuo sect-arena --sect {sect_command} {member_args} --framework {mission_framework}"

    command_lines = [
        mission_command,
        challenge_command,
        upload_command,
        ranking_command,
        card_command,
        badge_command,
        quest_command,
        campaign_command,
        sect_hall_command,
        sect_quest_command,
        sect_arena_command,
    ]

    return "\n".join([
        "# Soul Ring Mission Hall",
        "",
        f"- GitHub: @{username}",
        f"- Target Framework: {framework_label} (`{mission_framework}`)",
        "- Current Snapshot Formula: current real CyberHuaTuo knowledge-base counts; rank appears only after at least one real prescription.",
        f"- Real prescriptions: {count_text}",
        f"- {framework_label} prescriptions: {framework_count}",
        f"- Global Rank: {rank_line}",
        f"- Status: {status_line}",
        "",
        "## Mission 1: First Soul Ring Prescription",
        f"- GitHub issue form: {issue_url}",
        f"- Start in CLI: `{challenge_command}`",
        f"- Publish accepted fix: `{upload_command}`",
        "",
        "## Mission 2: PR Settlement",
        f"- PR template: `{pr_template}`",
        f"- PR auto-comment workflow: `{pr_workflow}`",
        f"- After review: `{ranking_command}` then `{card_command}`",
        "",
        "## Mission 3: Personal Soul Ring",
        "```bash",
        challenge_command,
        quest_command,
        upload_command,
        ranking_command,
        card_command,
        badge_command,
        campaign_command,
        "```",
        "",
        "## Mission 4: Sect / Team Growth",
        f"- Sect: {sect}",
        f"- Members: {', '.join('@' + member for member in normalized_members)}",
        "```bash",
        sect_hall_command,
        sect_quest_command,
        sect_arena_command,
        "```",
        "",
        "## Share Post",
        "```text",
        (
            f"@{username} opened a CyberHuaTuo Soul Ring Mission Hall for "
            f"{framework_label}: {count_text}, Global Rank {rank_line}."
        ),
        f"Next action: {challenge_command}",
        f"Join: {repo_url}",
        *_candidate_first_install_copy_lines(),
        "#CyberHuaTuo #SoulRingMission #AIAgents",
        "```",
        "",
        "## Agent Prompt",
        "```text",
        (
            f"Use CyberHuaTuo to guide @{username} through the Soul Ring Mission Hall. "
            f"Start with a real {framework_label} issue, publish only a verified prescription, "
            "then generate the personal card and sect hall."
        ),
        "Run these commands:",
        *command_lines,
        "```",
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "Rule: this mission hall reports current real contribution data only; progress and ranks are not invented.",
    ])


def format_soul_ring_launch_scroll(
    github_username: str = "your-github-username",
    framework: str = "langchain",
    release_tag: str = "",
) -> str:
    """Generate a marketplace launch scroll that routes attention into the first-ring loop."""
    username = github_username.strip().lstrip("@") or "your-github-username"
    target_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(target_framework)
    release = release_tag.strip() or f"v{__version__}"
    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"
    issue_url = f"{repo_url}/issues/new?template=soul-ring-prescription.yml"

    install_commands = [
        *_candidate_first_install_commands(release),
        f"cyberhuatuo launch --username {username} --framework {target_framework} --release-tag {release}",
        f"cyberhuatuo launch-campaign --username {username} --framework {target_framework} --release-tag {release} --target-contributors 3",
    ]
    first_ring_commands = [
        f"cyberhuatuo challenge --username {username} --framework {target_framework}",
        f"cyberhuatuo mission --username {username} --framework {target_framework}",
        f"cyberhuatuo ladder {username} --framework {target_framework}",
        f"cyberhuatuo campaign {username} --framework {target_framework}",
    ]
    marketplace_commands = [
        "python -m build --sdist --wheel",
        "python scripts/check_release_boundary.py",
        "claude plugin validate .",
        "mcpb validate claude-desktop",
        "mcpb pack claude-desktop dist/cyberhuatuo-claude-desktop.mcpb",
        "codex mcp add cyberhuatuo -- uvx --from cyberhuatuo cyberhuatuo-mcp",
        "codex mcp list",
    ]

    return "\n".join([
        "# Soul Ring Launch Scroll",
        "",
        f"- Release: `{release}`",
        f"- Target contributor: @{username}",
        f"- First-ring direction: {framework_label} (`{target_framework}`)",
        "- Launch Asset Formula: current repository release assets and public commands; public progress comes only from real CyberHuaTuo contribution records.",
        "",
        "## Marketplace Spine",
        "- PyPI: `cyberhuatuo`",
        "- MCP entrypoint: `cyberhuatuo-mcp`",
        "- Claude Code: `.claude-plugin/plugin.json`",
        "- Claude Desktop MCPB: `claude-desktop/manifest.json`",
        "- Claude MCPB workflow: `.github/workflows/package-claude-mcpb.yml`",
        "- Codex: `.codex-plugin/plugin.json`",
        "- Shared MCP config: `.mcp.json`",
        "- Privacy policy: `docs/PRIVACY.md`",
        "",
        "## Install / Verify",
        "```bash",
        *install_commands,
        *marketplace_commands,
        "```",
        "",
        "## First Ring Funnel",
        "- Web entry: First Soul Ring Prescription",
        f"- Issue form: {issue_url}",
        "- Promotion workflow: `.github/workflows/soul-ring-promote.yml`",
        "- Maintainer action: add `accepted-prescription` to a real, verified First Soul Ring issue.",
        "",
        "```bash",
        *first_ring_commands,
        "```",
        "",
        "## GitHub Discussion / Release Post",
        "````markdown",
        f"CyberHuaTuo {release} is ready for PyPI, Claude, Codex, and MCP clients.",
        "",
        "Install:",
        "```bash",
        *_candidate_first_install_commands(release),
        "```",
        "",
        f"Start the First Soul Ring path for {framework_label}:",
        "```bash",
        f"cyberhuatuo challenge --username {username} --framework {target_framework}",
        f"cyberhuatuo mission --username {username} --framework {target_framework}",
        "```",
        "",
        f"Submit a real fix: {issue_url}",
        "No adoption numbers, fake champions, or historical seasons are invented.",
        "````",
        "",
        "## X / Weibo",
        "```text",
        (
            f"CyberHuaTuo {release}: AI-agent debugging clinic + MCP + Codex/Claude skills + "
            "a real First Soul Ring contribution ladder."
        ),
        *_candidate_first_install_copy_lines(release),
        f"First ring: cyberhuatuo challenge --username {username} --framework {target_framework}",
        "#CyberHuaTuo #SoulRing #MCP #AIAgents",
        "```",
        "",
        "## Agent Prompt",
        "```text",
        (
            "Use CyberHuaTuo as an MCP debugging clinic. Install it, diagnose one real AI-agent "
            f"failure, then route @{username} through the First Soul Ring funnel for {framework_label}. "
            "Only accept real symptoms, root causes, fixes, and verification evidence."
        ),
        "Run:",
        *first_ring_commands,
        "```",
        "",
        "Rule: No adoption numbers, fake champions, or historical seasons are invented. The launch scroll is a funnel, not a vanity metric sheet.",
    ])


def _clamp_launch_target(value: int | str | None, default: int = 3) -> int:
    try:
        target = int(value) if value is not None else default
    except (TypeError, ValueError):
        target = default
    if target <= 0:
        target = default
    return max(1, min(target, 100))


def _command_text(value: str, default: str) -> str:
    text = (value or "").strip() or default
    return text.replace('"', "'").replace("\r", " ").replace("\n", " ")[:160]


def format_soul_ring_launch_campaign(
    github_username: str = "your-github-username",
    framework: str = "langchain",
    release_tag: str = "",
    target_contributors: int | str = 3,
    surface: str = "PyPI / Claude / Codex launch",
) -> str:
    """Generate a cold-start market launch campaign tied to the real growth ledger."""
    username = github_username.strip().lstrip("@") or "your-github-username"
    target_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(target_framework)
    release = release_tag.strip() or f"v{__version__}"
    target = _clamp_launch_target(target_contributors)
    launch_surface = _command_text(surface, "PyPI / Claude / Codex launch")

    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"
    first_ring_issue_url = f"{repo_url}/issues/new?template=soul-ring-prescription.yml"
    growth_issue_params = {
        "template": "soul-ring-growth-flywheel.yml",
        "title": f"[Soul Ring Growth] launch campaign for {username}",
        "github_username": username,
        "framework": target_framework,
        "growth_surface": launch_surface,
        "real_signal": (
            f"CyberHuaTuo {release} launch campaign targeting {target} first-ring contributors. "
            "Campaign-specific conversions must be recorded with activation ledger events."
        ),
        "bottleneck_guess": "Cold launch: external attention must convert into first real prescriptions.",
        "campaign_hook": (
            f"Recruit {target} first-ring contributors through install, challenge, mission, share proof, and leaderboard loops."
        ),
    }
    growth_issue_url = f"{repo_url}/issues/new?{urlencode(growth_issue_params)}"
    share_issue_params = {
        "template": "soul-ring-share-proof.yml",
        "title": f"[Soul Ring Share Proof] {target_framework} launch campaign share proof",
        "github_username": username,
        "framework": target_framework,
        "proof_context": f"Public share proof for the {release} Soul Ring Launch Campaign.",
    }
    share_issue_url = f"{repo_url}/issues/new?{urlencode(share_issue_params)}"

    profile = get_cultivation_profile(username)
    contribution_count = int(profile.get("contribution_count", 0))
    framework_count = int(count_contributor_cases_by_framework(username).get(target_framework, 0))
    global_stats = get_global_ranking_stats()
    observed_contributors = sorted(
        str(actor).lstrip("@")
        for actor, count in global_stats.items()
        if str(actor).strip() and int(count or 0) > 0
    )
    global_total = len(observed_contributors)
    observed_count = global_total
    shortfall = max(target - observed_count, 0)
    next_target = min(target + max(3, target), 100) if observed_count >= target else target
    next_target_rule = (
        "if observed contributors reach the current target, next target = min(current target + max(3, current target), 100); "
        "otherwise keep the current target and recruit the shortfall."
    )
    observed_identities = (
        ", ".join(f"@{actor}" for actor in observed_contributors)
        if observed_contributors
        else "none yet"
    )

    launch_command = (
        f"cyberhuatuo launch-campaign --username {username} --framework {target_framework} "
        f"--release-tag {release} --target-contributors {target}"
    )
    next_growth_campaign_command = (
        f"cyberhuatuo launch-campaign --username {username} --framework {target_framework} "
        f"--release-tag {release} --target-contributors {next_target}"
    )
    market_ready_command = (
        f"cyberhuatuo market-ready --remote --strict-remote --username {username} "
        f"--framework {target_framework} --release-tag {release} --target-contributors {target}"
    )
    proof_pack_command = (
        f"cyberhuatuo proof-pack --username {username} --framework {target_framework} "
        f"--release-tag {release} --target-contributors {target}"
    )
    market_copy_command = (
        f"cyberhuatuo market-copy --username {username} --framework {target_framework} "
        f"--release-tag {release} --target-contributors {target}"
    )
    record_return_command = (
        f"cyberhuatuo record-return --username {username} --framework {target_framework} "
        f'--surface "{launch_surface}" --source-url <https-url>'
    )
    record_session_command = (
        f"cyberhuatuo record-session --username {username} --framework {target_framework} "
        '--surface "First agent session from launch campaign" --source-url <https-url>'
    )
    activation_command = f"cyberhuatuo activation --username {username} --framework {target_framework} --top-n 10"
    flywheel_command = f"cyberhuatuo flywheel --username {username} --framework {target_framework} --top-n 10"
    challenge_command = f"cyberhuatuo challenge --username {username} --framework {target_framework}"
    mission_command = f"cyberhuatuo mission --username {username} --framework {target_framework}"
    campaign_pack_command = f"cyberhuatuo campaign {username} --framework {target_framework}"
    record_share_command = f"cyberhuatuo record-share --username {username} --framework {target_framework} --share-url <https-url>"
    share_report_command = f"cyberhuatuo share-report --username {username} --framework {target_framework} --top-n 10"
    share_leaderboard_command = f"cyberhuatuo share-leaderboard --framework {target_framework} --top-n 10"
    season_command = f"cyberhuatuo season --framework {target_framework} --top-n 10"
    proof_recording_command = (
        f"cyberhuatuo traction-proof --username {username} --framework {target_framework} "
        f"--release-tag {release} --target-contributors {target} --record-snapshot"
    )
    recap_copy = (
        f"CyberHuaTuo {release} Soul Ring Launch Campaign recap: {observed_count} / {target} "
        f"real first-ring contributors observed; shortfall {shortfall}. "
        f"Next sprint target: {next_target}. Proof: run `{proof_recording_command}`."
    )

    command_lines = [
        launch_command,
        proof_pack_command,
        market_copy_command,
        market_ready_command,
        proof_recording_command,
        next_growth_campaign_command,
        *_candidate_first_install_commands(release),
        record_return_command,
        record_session_command,
        activation_command,
        flywheel_command,
        challenge_command,
        mission_command,
        campaign_pack_command,
        record_share_command,
        share_report_command,
        share_leaderboard_command,
        season_command,
    ]

    stage_rows = [
        "| Stage | Real Signal | Next Command |",
        "|---|---|---|",
        f"| Market launch | `{release}` on {launch_surface}; install commands available | `{record_return_command}` |",
        f"| First-session exposure | Campaign-specific conversions: missing until record-return / record-session / record-share events exist | `{record_session_command}` |",
        f"| First Soul Ring | @{username}: {contribution_count} total prescription(s), {framework_count} {framework_label} prescription(s) | `{challenge_command}` |",
        f"| Public share proof | campaign-specific conversions are not inferred from downloads or stars | `{record_share_command}` |",
        f"| Proof leaderboard | rank only reviewable public share URLs from the local ledger | `{share_leaderboard_command}` |",
    ]

    return "\n".join([
        "# Soul Ring Launch Campaign",
        "",
        f"- Release: `{release}`",
        f"- Campaign Owner: @{username}",
        f"- First-ring Direction: {framework_label} (`{target_framework}`)",
        f"- Campaign Target: {target} first-ring contributors",
        f"- Current real ranked contributors: {global_total}",
        "- Campaign-specific conversions: missing until record-return / record-session / record-share events exist.",
        "- Real Data Formula: current contribution snapshots plus local activation ledger events; no external analytics are backfilled.",
        "- No downloads, retention, repost counts, referrals, rewards, or Spirit Power are invented.",
        "",
        "## Campaign Recap And Next Sprint",
        f"- Observed real contributors: {observed_count} / {target}",
        f"- Observed contributor identities: {observed_identities}",
        f"- Campaign shortfall: {shortfall} first-ring contributor(s)",
        f"- Next target rule: {next_target_rule}",
        f"- Next sprint target: {next_target} first-ring contributors",
        f"- Next growth_campaign command: `{next_growth_campaign_command}`",
        f"- No-network proof pack command: `{proof_pack_command}`",
        f"- Marketplace submission copy command: `{market_copy_command}`",
        f"- Proof recording command: `{proof_recording_command}`",
        f"- Launch Closure Checklist command: `{market_ready_command}`",
        "- Recap copy:",
        "```text",
        recap_copy,
        "```",
        "",
        "## Public Issue Routes",
        f"- Prefilled Growth Flywheel Issue: {growth_issue_url}",
        f"- Prefilled Share Proof Issue: {share_issue_url}",
        f"- First Soul Ring Prescription: {first_ring_issue_url}",
        f"- Launch Campaign Issue Template: {repo_url}/issues/new?template=soul-ring-launch-campaign.yml",
        "",
        "## Launch Closure Checklist",
        "- Close remote acquisition routes, PyPI Trusted Publisher, GitHub release trigger, registry latest-version proof, first public proof, and recheck commands before claiming the campaign is market-ready.",
        "```bash",
        proof_pack_command,
        market_copy_command,
        market_ready_command,
        "```",
        "",
        "## Campaign Operating Loop",
        *stage_rows,
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "## GitHub Discussion / Release Post",
        "````markdown",
        f"### CyberHuaTuo {release} Soul Ring Launch Campaign",
        "",
        f"Target: recruit {target} first-ring contributors for {framework_label}.",
        "",
        "Campaign recap:",
        "```text",
        recap_copy,
        "```",
        "",
        "Install:",
        "```bash",
        *_candidate_first_install_commands(release),
        "```",
        "",
        "Run the public loop:",
        "```bash",
        *command_lines,
        "```",
        "",
        f"Growth issue: {growth_issue_url}",
        f"Share proof issue: {share_issue_url}",
        "No downloads, retention, repost counts, referrals, rewards, or Spirit Power are invented.",
        "````",
        "",
        "## X / Weibo",
        "```text",
        f"CyberHuaTuo {release} launch campaign: recruit {target} real First Soul Ring contributors for {framework_label}.",
        f"Recap: {observed_count}/{target} observed, shortfall {shortfall}; next sprint target {next_target}.",
        *_candidate_first_install_copy_lines(release),
        f"Start: {challenge_command}",
        f"Proof board: {share_leaderboard_command}",
        "#CyberHuaTuo #SoulRing #MCP #AIAgents",
        "```",
        "",
        "## Agent Prompt",
        "```text",
        (
            f"Run the CyberHuaTuo {release} Soul Ring Launch Campaign for @{username}. "
            f"Target {target} real first-ring contributors in {framework_label}. "
            f"Current recap: {observed_count} observed, {shortfall} shortfall, next sprint target {next_target}. "
            "Use only real public URLs, activation ledger events, and verified prescriptions. "
            "Do not infer success from downloads, stars, reposts, or private claims."
        ),
        "Run:",
        *command_lines,
        "```",
    ])


def format_soul_ring_growth_flywheel(
    github_username: str = "your-github-username",
    framework: str = "langchain",
    sect_name: str = "CyberHuaTuo Sect",
    members: list[str] | tuple[str, ...] | str | None = None,
    top_n: int = 10,
) -> str:
    """Generate a real-data growth flywheel snapshot for the soul-ring loop."""
    username = github_username.strip().lstrip("@") or "your-github-username"
    target_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(target_framework)
    try:
        board_size = int(top_n)
    except (TypeError, ValueError):
        board_size = 10
    board_size = max(1, min(board_size, 50))

    profile = get_cultivation_profile(username)
    contribution_count = int(profile.get("contribution_count", 0))
    framework_counts = count_contributor_cases_by_framework(username)
    framework_count = int(framework_counts.get(target_framework, 0))
    next_ring = get_next_soul_ring_progress(framework_count)
    next_gate = framework_count if next_ring.get("is_max") else framework_count + int(next_ring.get("needed", 0))
    if next_gate <= 0:
        next_gate = 1

    raw_members = members if members is not None else [username]
    normalized_members = _normalize_sect_members(raw_members)
    member_keys = {member.lower() for member in normalized_members}
    if username.lower() not in member_keys:
        normalized_members.insert(0, username)

    sect = sect_name.strip() or "CyberHuaTuo Sect"
    sect_command = _format_sect_command_name(sect)
    member_args = " ".join(normalized_members)
    member_snapshots = []
    for member in normalized_members:
        member_profile = get_cultivation_profile(member)
        member_count = int(member_profile.get("contribution_count", 0))
        member_frameworks = count_contributor_cases_by_framework(member)
        member_snapshots.append({
            "username": member,
            "count": member_count,
            "framework_count": int(member_frameworks.get(target_framework, 0)),
            "rank": _format_duel_rank(member_profile),
        })

    activated_members = sum(1 for snapshot in member_snapshots if snapshot["count"] > 0)
    member_total = len(member_snapshots) or 1
    global_stats = get_global_ranking_stats()
    global_total = len(global_stats)
    leaderboard_signal = (
        f"{global_total} ranked contributors in current global snapshot"
        if global_total
        else "empty current snapshot"
    )

    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"
    issue_url = f"{repo_url}/issues/new?template=soul-ring-prescription.yml"
    launch_command = f"cyberhuatuo launch --username {username} --framework {target_framework} --release-tag v{__version__}"
    record_return_command = (
        f"cyberhuatuo record-return --username {username} --framework {target_framework} "
        '--surface "Agent community prompt" --source-url <https-url>'
    )
    activation_command = (
        f"cyberhuatuo activation --username {username} --framework {target_framework} "
        f"--sect {sect_command} --members {member_args} --top-n {board_size}"
    )
    challenge_command = f"cyberhuatuo challenge --username {username} --framework {target_framework}"
    bounty_command = (
        f"cyberhuatuo bounty --username {username} --framework auto --top-n {board_size} "
        f"--release-tag v{__version__} --target-contributors 3"
    )
    quest_command = f"cyberhuatuo quest {username} --framework {target_framework}"
    ladder_command = f"cyberhuatuo ladder {username} --framework {target_framework}"
    campaign_command = f"cyberhuatuo campaign {username} --framework {target_framework}"
    record_share_command = f"cyberhuatuo record-share --username {username} --framework {target_framework} --share-url <https-url>"
    share_report_command = f"cyberhuatuo share-report --username {username} --framework {target_framework} --top-n {board_size}"
    share_leaderboard_command = f"cyberhuatuo share-leaderboard --framework {target_framework} --top-n {board_size}"
    launch_campaign_command = (
        f"cyberhuatuo launch-campaign --username {username} --framework {target_framework} "
        f"--release-tag v{__version__} --target-contributors 3"
    )
    market_ready_command = (
        f"cyberhuatuo market-ready --remote --strict-remote --username {username} "
        f"--framework {target_framework} --release-tag v{__version__} --target-contributors 3"
    )
    leaderboard_command = f"cyberhuatuo leaderboard --top-n {board_size}"
    season_command = f"cyberhuatuo season --framework {target_framework} --top-n {board_size}"
    sect_arena_command = f"cyberhuatuo sect-arena --sect {sect_command} {member_args} --framework {target_framework}"
    flywheel_command = (
        f"cyberhuatuo flywheel --username {username} --framework {target_framework} "
        f"--sect {sect_command} --members {member_args} --top-n {board_size}"
    )

    if contribution_count <= 0:
        primary_bottleneck = "First-ring activation"
        bottleneck_detail = "First real prescription unlocks every downstream loop."
    elif activated_members < member_total:
        primary_bottleneck = "Collaboration / sect"
        bottleneck_detail = "At least one named sect member has not lit a real first ring yet."
    elif not next_ring.get("is_max") and int(next_ring.get("needed", 0)) > 0:
        primary_bottleneck = "Repeat contribution"
        bottleneck_detail = "The active contributor has a visible next-ring gate in the target framework."
    else:
        primary_bottleneck = "Public sharing"
        bottleneck_detail = "Contribution data exists, but external sharing telemetry is still missing."

    first_ring_signal = f"{1 if contribution_count > 0 else 0} / 1 first-ring prescriptions"
    repeat_signal = f"{framework_count} / {next_gate} {framework_label} prescriptions"
    collaboration_signal = f"{activated_members} / {member_total} activated members"
    sharing_signal = "no public share proof recorded yet; not treated as proven zero propagation"
    sharing_bottleneck = "first public share proof missing"
    sharing_next_command = record_share_command
    try:
        from .activation import build_share_proof_leaderboard

        share_board = build_share_proof_leaderboard(target_framework, board_size)
        share_events_count = len(share_board["share_events"])
        current_share_score = 0
        latest_share_url = ""
        for row in share_board["rows"]:
            if str(row["username"]).lower() == username.lower():
                current_share_score = int(row["score"])
                latest_share_url = str(row.get("latest_share_url", ""))
                break
        if share_events_count:
            sharing_signal = (
                f"Public share proof: {share_events_count} reviewable share URL(s); "
                f"@{username} share proof score {current_share_score}"
            )
            if latest_share_url:
                sharing_signal += f"; latest proof {latest_share_url}"
            sharing_bottleneck = "review share leaderboard"
            sharing_next_command = share_leaderboard_command
        else:
            ledger_missing = any("activation ledger missing" in warning for warning in share_board["warnings"])
            if ledger_missing:
                sharing_signal = "public share proof ledger missing; not treated as proven zero propagation"
    except Exception as exc:
        sharing_signal = f"share proof ledger unavailable: {exc}; not treated as proven zero propagation"
        sharing_bottleneck = "share proof ledger unavailable"
    marketplace_signal = "release assets and install commands present; activation ledger: use record-return; downloads: missing"
    next_command = flywheel_command
    campaign_hook = (
        f"Campaign hook: convert {primary_bottleneck.lower()} into the next public action with "
        f"`{campaign_command}` and `{next_command}`."
    )
    real_signal_context = (
        f"Generated by cyberhuatuo flywheel from current real CyberHuaTuo contribution records: "
        f"@{username}, {framework_label}, {first_ring_signal}, {repeat_signal}, "
        f"{collaboration_signal}, global leaderboard {leaderboard_signal}. "
        "Downloads, retention, and attribution are missing unless linked here."
    )
    bottleneck_context = (
        f"Primary bottleneck: {primary_bottleneck}. {bottleneck_detail} "
        f"Next command: {next_command}"
    )
    flywheel_issue_params = {
        "template": "soul-ring-growth-flywheel.yml",
        "title": f"[Soul Ring Growth] {primary_bottleneck} for {username}",
        "github_username": username,
        "framework": target_framework,
        "growth_surface": "Agent community prompt",
        "real_signal": real_signal_context,
        "bottleneck_guess": bottleneck_context,
        "campaign_hook": campaign_hook,
    }
    prefilled_flywheel_issue_url = f"{repo_url}/issues/new?{urlencode(flywheel_issue_params)}"

    table_rows = [
        "| Stage | Current Real Signal | Bottleneck | Next Command |",
        "|---|---|---|---|",
        (
            "| Marketplace attention -> First Soul Ring | "
            f"{marketplace_signal} | attribution missing | `{record_return_command}` |"
        ),
        (
            "| First-ring activation | "
            f"{first_ring_signal} | {'blocked' if contribution_count <= 0 else 'active'} | `{challenge_command}` |"
        ),
        (
            "| Repeat contribution | "
            f"{repeat_signal} | {'next gate visible' if framework_count < next_gate else 'max gate or satisfied'} | "
            f"`{quest_command}` |"
        ),
        (
            "| Collaboration / sect | "
            f"{collaboration_signal} | {'needs member activation' if activated_members < member_total else 'active'} | "
            f"`{sect_arena_command}` |"
        ),
        (
            "| Public sharing | "
            f"{sharing_signal} | {sharing_bottleneck} | `{sharing_next_command}` |"
        ),
    ]

    member_rows = [
        "| Member | Real prescriptions | Framework prescriptions | Global rank |",
        "|---|---:|---:|---|",
    ]
    for snapshot in member_snapshots:
        member_rows.append(
            f"| @{snapshot['username']} | {snapshot['count']} | "
            f"{snapshot['framework_count']} | {snapshot['rank']} |"
        )

    command_lines = [
        record_return_command,
        activation_command,
        flywheel_command,
        market_ready_command,
        launch_command,
        launch_campaign_command,
        leaderboard_command,
        bounty_command,
        quest_command,
        ladder_command,
        season_command,
        sect_arena_command,
        campaign_command,
        record_share_command,
        share_report_command,
        share_leaderboard_command,
    ]

    return "\n".join([
        "# Soul Ring Growth Flywheel",
        "",
        f"- GitHub: @{username}",
        f"- Target Framework: {framework_label} (`{target_framework}`)",
        f"- Sect / Team: {sect}",
        "- Snapshot Formula: current real CyberHuaTuo contribution records; no external analytics are backfilled.",
        f"- Global leaderboard: {leaderboard_signal}",
        f"- Primary Bottleneck: {primary_bottleneck}",
        f"- Bottleneck Detail: {bottleneck_detail}",
        "",
        "## External Metrics Disclosure",
        "- downloads: missing",
        "- retention: missing",
        "- attribution: missing",
        "- No downloads, retention, or attribution metrics are invented.",
        "",
        "## Activation Ledger",
        "- Ledger Formula: local JSONL events from `cyberhuatuo record-return`, `record-session`, and `record-share`; missing or unwritable ledgers are disclosed by `cyberhuatuo activation` and `cyberhuatuo share-report`.",
        f"- Launch Closure Checklist: `{market_ready_command}`",
        f"- Record external return: `{record_return_command}`",
        f"- Activation funnel: `{activation_command}`",
        f"- Launch campaign: `{launch_campaign_command}`",
        f"- Record public share attribution: `{record_share_command}`",
        f"- Share attribution report: `{share_report_command}`",
        f"- Share proof leaderboard: `{share_leaderboard_command}`",
        "",
        "## Flywheel Stages",
        *table_rows,
        "",
        "## Sect Activation Snapshot",
        *member_rows,
        "",
        "## Public Issue Routes",
        f"- Prefilled Growth Flywheel Issue: {prefilled_flywheel_issue_url}",
        f"- Growth Flywheel Issue Template: {repo_url}/issues/new?template=soul-ring-growth-flywheel.yml",
        f"- Share Proof Issue Template: {repo_url}/issues/new?template=soul-ring-share-proof.yml",
        f"- First Soul Ring Prescription: {issue_url}",
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        f"### Soul Ring Growth Flywheel: @{username}",
        "",
        f"**Framework:** {framework_label} (`{target_framework}`)",
        "**Snapshot formula:** current real CyberHuaTuo contribution records.",
        f"**Global leaderboard:** {leaderboard_signal}",
        f"**Primary bottleneck:** {primary_bottleneck}",
        f"**Why:** {bottleneck_detail}",
        "",
        "Run the current callable loop:",
        "```bash",
        *command_lines,
        "```",
        "",
        "No downloads, retention, or attribution metrics are invented.",
        "````",
        "",
        "## X / Weibo",
        "```text",
        (
            f"CyberHuaTuo Soul Ring Growth Flywheel for @{username}: "
            f"{first_ring_signal}, {collaboration_signal}, bottleneck = {primary_bottleneck}."
        ),
        f"Next action: {command_lines[0]}",
        f"Join: {repo_url}",
        "#CyberHuaTuo #SoulRing #MCP #AIAgents",
        "```",
        "",
        "## Agent Prompt",
        "```text",
        (
            f"Use CyberHuaTuo to inspect @{username}'s Soul Ring Growth Flywheel for "
            f"{framework_label}. Report only current contribution records, disclose missing downloads, "
            "retention, and attribution, then move the user through the primary bottleneck."
        ),
        "Run:",
        *command_lines,
        "```",
        "",
        "Rule: this flywheel snapshot is a real-data operating surface, not a vanity metric sheet. No downloads, retention, or attribution metrics are invented.",
    ])


def format_soul_ring_breakthrough_ladder(
    github_username: str = "your-github-username",
    framework: str = "langchain",
) -> str:
    """Generate a real-data Soul Ring breakthrough ladder for one target direction."""
    username = github_username.strip().lstrip("@") or "your-github-username"
    target_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(target_framework)
    target_key = get_direction_for_framework(target_framework)
    alchemy = get_alchemy_profile(username)
    target_direction = None

    if target_framework:
        target_direction = next(
            (direction for direction in alchemy.get("directions", []) if direction["key"] == target_key),
            None,
        )

    if target_direction is None:
        target_direction = alchemy.get("primary")

    if target_direction is None or target_direction.get("key") != target_key:
        direction_info = ALCHEMY_DIRECTIONS.get(target_key, ALCHEMY_DIRECTIONS["detox"])
        count = 0
        rings, ring_name, ring_count = calculate_soul_rings(count)
        target_direction = {
            "key": target_key,
            "emoji": direction_info[0],
            "name_cn": direction_info[1],
            "name_en": direction_info[2],
            "frameworks": [framework_label],
            "count": count,
            "rings": rings,
            "ring_name": ring_name,
            "ring_count": ring_count,
            "next_ring": get_next_soul_ring_progress(count),
        }

    direction_count = int(target_direction.get("count", 0))
    progress = get_next_soul_ring_progress(direction_count)
    evidence_progress = _build_evidence_progress(username, target_framework, direction_count)
    evidence_total = evidence_progress["total"]
    evidence_word = "prescription" if evidence_total == 1 else "prescriptions"
    evidence_submission_command = (
        f"cyberhuatuo evidence {username} --framework {target_framework} "
        "--amount 1 --source-url <reviewable-http-url>"
    )
    current_ring = (
        "not lit yet"
        if direction_count <= 0
        else f"{target_direction.get('rings', '')} {target_direction.get('ring_name', '')}".strip()
    )
    if progress["is_max"]:
        next_gate_line = "Nine-ring supreme already reached"
        needed_line = "0 real prescriptions"
    else:
        next_gate_line = _format_duel_delta(progress["next_min_count"])
        needed_line = _format_duel_delta(progress["needed"])

    ladder_rows = []
    for threshold, rings in sorted(_SOUL_RING_TIERS, key=lambda item: item[0]):
        ring_name = _SOUL_RING_TIER_NAMES[threshold]
        if direction_count >= threshold:
            status = "UNLOCKED"
            gap = "0 real prescriptions"
        elif not progress["is_max"] and threshold == progress["next_min_count"]:
            status = "NEXT"
            gap = _format_duel_delta(threshold - direction_count)
        else:
            status = "LOCKED"
            gap = _format_duel_delta(threshold - direction_count)
        ladder_rows.append(f"| {threshold} | {ring_name} | {rings} | {status} | {gap} |")

    challenge_command = f"cyberhuatuo challenge --username {username} --framework {target_framework}"
    quest_command = f"cyberhuatuo quest {username} --framework {target_framework}"
    upload_command = (
        'cyberhuatuo upload --title "<real issue title>" '
        '--prescription "<root cause and fix>" '
        f"--framework {target_framework} --contributor {username}"
    )
    ranking_command = f"cyberhuatuo ranking {username}"
    card_command = f"cyberhuatuo card {username}"
    badge_command = f"cyberhuatuo badge {username}"
    campaign_command = f"cyberhuatuo campaign {username} --framework {target_framework}"
    mission_command = f"cyberhuatuo mission --username {username} --framework {target_framework}"
    command_lines = [
        challenge_command,
        quest_command,
        upload_command,
        ranking_command,
        card_command,
        badge_command,
        campaign_command,
        mission_command,
        evidence_submission_command,
    ]

    thresholds = ", ".join(str(threshold) for threshold, _rings in sorted(_SOUL_RING_TIERS, key=lambda item: item[0]))
    return "\n".join([
        "# Soul Ring Breakthrough Ladder",
        "",
        f"- GitHub: @{username}",
        f"- Target Framework: {framework_label} (`{target_framework}`)",
        f"- Target Direction: {target_direction['name_en']} (`{target_direction['key']}`)",
        "- Breakthrough Formula: current real prescription count in the target alchemy direction; thresholds are "
        f"{thresholds}.",
        f"- Current Direction Count: {_format_duel_delta(direction_count)}",
        f"- Current Ring: {current_ring}",
        f"- Next Gate: {next_gate_line}",
        f"- Needed: {needed_line}",
        f"- Public Evidence Progress: {evidence_total} reviewable evidence-backed {evidence_word}",
        f"- Evidence-backed Count: {evidence_progress['evidence_backed_count']}",
        f"- Evidence Submission Command: `{evidence_submission_command}`",
        "- Evidence entries are append-only and reviewable; they do not mutate leaderboards until accepted prescriptions are imported.",
        "",
        "## Gate Ladder",
        "| Threshold | Ring | Display | Status | Gap |",
        "| --- | --- | --- | --- | --- |",
        *ladder_rows,
        "",
        "## Breakthrough Actions",
        "```bash",
        *command_lines,
        "```",
        "",
        "## Share Post",
        "```text",
        (
            f"@{username} is chasing the next CyberHuaTuo Soul Ring in {framework_label}: "
            f"{_format_duel_delta(direction_count)} now, next gate at {next_gate_line}, "
            f"{needed_line} needed."
        ),
        f"Next action: {quest_command}",
        *_candidate_first_install_copy_lines(),
        "#CyberHuaTuo #SoulRingBreakthrough #AIAgents",
        "```",
        "",
        "Rule: this breakthrough ladder reports current real contribution data only; progress, ranks, and gates are not invented.",
    ])


def _format_prescription_count(count: int) -> str:
    word = "prescription" if count == 1 else "prescriptions"
    return f"{count} {word}"


def _format_shields_segment(text: str) -> str:
    """Encode one Shields.io static badge path segment."""
    normalized = str(text).strip() or "none"
    normalized = normalized.replace("_", "__").replace("-", "--").replace(" ", "_")
    return quote(normalized, safe="")


def _build_static_badge_url(label: str, message: str, color: str) -> str:
    label_part = _format_shields_segment(label)
    message_part = _format_shields_segment(message)
    color_part = color.lstrip("#")
    return (
        f"https://img.shields.io/badge/{label_part}-{message_part}-{color_part}"
        "?style=for-the-badge&labelColor=0A0E1A&logo=github&logoColor=white"
    )


def format_profile_badge_kit(github_username: str) -> str:
    """Generate copy-ready GitHub Profile / README badge markdown."""
    username = github_username.strip() or "your-github-username"
    profile = get_cultivation_profile(username)
    alchemy = get_alchemy_profile(username)
    fw_counts = count_contributor_cases_by_framework(username)

    contribution_count = int(profile.get("contribution_count", 0))
    count_text = _format_prescription_count(contribution_count)
    title_en = profile.get("title_en", "Intern Apprentice")
    badge_url = _build_static_badge_url("CyberHuaTuo", f"{title_en} · {count_text}", "00D09C")
    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"
    badge_markdown = f"[![CyberHuaTuo Soul Ring]({badge_url})]({repo_url})"

    challenge_framework = (
        max(fw_counts.items(), key=lambda item: item[1])[0] if fw_counts else "langchain"
    )

    primary = alchemy.get("primary")
    if primary:
        frameworks = ", ".join(primary.get("frameworks", [])[:3]) or primary["name_en"]
        current_ring = (
            f"{primary['emoji']} {primary['name_cn']} / {primary['name_en']} · "
            f"{primary['rings']} {primary['ring_name']} · {frameworks}"
        )
        next_ring = primary["next_ring"]["hint_cn"]
    else:
        frameworks = "尚未点亮魂环"
        current_ring = "尚未点亮魂环"
        next_ring = "下一环: 白环 · 贡献 1 方真实药方即可点亮。"

    if contribution_count > 0:
        rank_line = f"Global Rank: #{profile['global_rank']} / {profile['global_total']}"
    else:
        rank_line = "Global Rank: not ranked yet"

    return "\n".join([
        "# 🔮 CyberHuaTuo GitHub Profile Badge Kit",
        "",
        "把下面这段 Markdown 贴到你的 GitHub Profile、项目 README 或贡献墙里：",
        "",
        "```markdown",
        badge_markdown,
        "```",
        "",
        badge_markdown,
        "",
        f"- GitHub: @{username}",
        f"- Title: {profile['title_emoji']} {profile['title_cn']} · {title_en}",
        f"- Prescriptions: {count_text}",
        f"- {rank_line}",
        f"- Primary Direction: {frameworks}",
        f"- Current Soul Ring: {current_ring}",
        f"- 下一环 / Next Ring: {next_ring}",
        "",
        "继续追环：",
        "```bash",
        f"cyberhuatuo challenge --username {username} --framework {challenge_framework}",
        f"cyberhuatuo badge {username}",
        f"cyberhuatuo card {username}",
        "```",
        "",
        "规则：徽章只展示当前可追溯贡献数据；没有真实药方时，不显示虚假排名或虚假魂环。",
    ])


# ============================================================
# 📋 分享卡片生成器
# ============================================================


def _select_quest_framework(fw_counts: dict[str, int], framework: str = "") -> str:
    requested = framework.strip()
    if requested:
        return requested
    if fw_counts:
        return max(fw_counts.items(), key=lambda item: item[1])[0]
    return "langchain"


def _format_quest_repo_line(framework: str) -> tuple[str, str]:
    from .issue_miner import get_target_repo

    target_repo = get_target_repo(framework)
    if not target_repo:
        return (
            "未登记固定淘金仓库",
            "cyberhuatuo mine search --repo owner/repo --limit 5",
        )

    full_name = f"{target_repo.owner}/{target_repo.repo}"
    return (
        full_name,
        f"cyberhuatuo mine search --repo {full_name} --limit 5",
    )


def format_soul_ring_quest_board(github_username: str, framework: str = "") -> str:
    """Generate a real-data Soul Ring quest board for the next contribution."""
    username = github_username.strip() or "your-github-username"
    profile = get_cultivation_profile(username)
    fw_counts = count_contributor_cases_by_framework(username)
    quest_framework = _select_quest_framework(fw_counts, framework)
    framework_label = _format_framework_label(quest_framework)
    alchemy = get_alchemy_profile(username)

    target_direction = None
    target_key = get_direction_for_framework(quest_framework)
    for direction in alchemy.get("directions", []):
        if direction["key"] == target_key:
            target_direction = direction
            break

    if target_direction:
        current_ring = (
            f"{target_direction['emoji']} {target_direction['name_cn']} / "
            f"{target_direction['name_en']} · {target_direction['rings']} "
            f"{target_direction['ring_name']}"
        )
        next_hint = target_direction["next_ring"]["hint_cn"]
        current_count = target_direction["count"]
    else:
        current_ring = "尚未点亮魂环"
        next_hint = "第一魂环: 白环 · 贡献 1 方真实药方即可点亮。"
        current_count = 0

    repo_display, mine_command = _format_quest_repo_line(quest_framework)
    rank_line = (
        f"#{profile['global_rank']} / {profile['global_total']}"
        if profile.get("contribution_count", 0) > 0
        else "not ranked yet"
    )

    return "\n".join([
        "# 🔮 追环任务板 / Soul Ring Quest Board",
        "",
        f"- Alchemist: @{username}",
        f"- Title: {profile['title_emoji']} {profile['title_cn']} · {profile['title_en']}",
        f"- Global Rank: {rank_line}",
        f"- Target Framework: {framework_label} (`{quest_framework}`)",
        f"- Target Repo: {repo_display}",
        f"- Current Soul Ring: {current_ring}",
        f"- Direction Prescriptions: {current_count}",
        f"- 下一环 / Next Ring: {next_hint}",
        "",
        "## Quest 1 · 淘一个真实问题",
        "```bash",
        mine_command,
        "```",
        "",
        "## Quest 2 · 把真实修复炼成药方",
        "```bash",
        (
            'cyberhuatuo upload --title "Fix real agent issue" '
            '--prescription "Record the real error, root cause, versions, and fix" '
            f"--framework {quest_framework} --contributor {username}"
        ),
        "```",
        "",
        "## Quest 3 · 亮出你的魂环",
        "```bash",
        f"cyberhuatuo badge {username}",
        f"cyberhuatuo card {username}",
        "```",
        "",
        "新手入口：",
        "```bash",
        f"cyberhuatuo challenge --username {username} --framework {quest_framework}",
        "```",
        "",
        "规则：只追踪真实仓库、真实 issue、真实药方；不展示未发生的贡献或虚假排名。",
    ])


def format_soul_ring_campaign_pack(github_username: str, framework: str = "") -> str:
    """Generate copy-ready multi-channel Soul Ring campaign copy from real profile data."""
    username = github_username.strip() or "your-github-username"
    profile = get_cultivation_profile(username)
    fw_counts = count_contributor_cases_by_framework(username)
    campaign_framework = _select_quest_framework(fw_counts, framework)
    framework_label = _format_framework_label(campaign_framework)
    alchemy = get_alchemy_profile(username)

    contribution_count = int(profile.get("contribution_count", 0))
    count_text = _format_prescription_count(contribution_count)
    rank_line = (
        f"#{profile['global_rank']} / {profile['global_total']}"
        if contribution_count > 0
        else "not ranked yet"
    )

    target_direction = None
    target_key = get_direction_for_framework(campaign_framework)
    for direction in alchemy.get("directions", []):
        if direction["key"] == target_key:
            target_direction = direction
            break

    if target_direction:
        framework_names = ", ".join(target_direction.get("frameworks", [])[:3]) or framework_label
        current_ring = (
            f"{target_direction['emoji']} {target_direction['name_cn']} / "
            f"{target_direction['name_en']} · {target_direction['rings']} "
            f"{target_direction['ring_name']} · {framework_names}"
        )
        next_ring = target_direction["next_ring"]["hint_cn"]
    else:
        framework_names = "not lit yet / 尚未点亮魂环"
        current_ring = "not lit yet / 尚未点亮魂环"
        next_ring = "first soul ring: contribute 1 real prescription / 第一魂环: 白环 · 贡献 1 方真实药方即可点亮。"

    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"
    badge_url = _build_static_badge_url(
        "CyberHuaTuo",
        f"{profile['title_en']} · {count_text}",
        "00D09C",
    )
    badge_markdown = f"[![CyberHuaTuo Soul Ring]({badge_url})]({repo_url})"
    quest_command = f"cyberhuatuo quest {username} --framework {campaign_framework}"
    challenge_command = f"cyberhuatuo challenge --username {username} --framework {campaign_framework}"

    command_lines = []
    if contribution_count == 0:
        command_lines.append(challenge_command)
    command_lines.extend([
        quest_command,
        f"cyberhuatuo badge {username}",
        f"cyberhuatuo card {username}",
    ])

    return "\n".join([
        "# 🔮 Soul Ring Campaign Pack",
        "",
        f"- Alchemist: @{username}",
        f"- Title: {profile['title_emoji']} {profile['title_cn']} / {profile['title_en']}",
        f"- Prescriptions: {count_text}",
        f"- Global Rank: {rank_line}",
        f"- Target Framework: {framework_label} (`{campaign_framework}`)",
        f"- Current Soul Ring: {current_ring}",
        f"- Next Ring: {next_ring}",
        "",
        "## GitHub Profile / README",
        "```markdown",
        badge_markdown,
        "",
        "I am building a verifiable AI-agent fix record with CyberHuaTuo.",
        f"- Soul Ring: {current_ring}",
        f"- Target: {framework_label} · {framework_names}",
        f"- Next action: `{quest_command}`",
        "```",
        "",
        "## X / Weibo",
        "```text",
        (
            f"I am chasing my next CyberHuaTuo soul ring: @{username} · "
            f"{profile['title_en']} · {count_text} · Global Rank {rank_line}."
        ),
        f"Current ring: {current_ring}",
        f"Next ring: {next_ring}",
        f"Join the challenge: {repo_url}",
        *_candidate_first_install_copy_lines(),
        "#CyberHuaTuo #SoulRing #AIAgents",
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        f"### 🔮 CyberHuaTuo Soul Ring Challenge: @{username}",
        "",
        f"- Real prescriptions: **{count_text}**",
        f"- Global Rank: **{rank_line}**",
        f"- Current Soul Ring: **{current_ring}**",
        f"- Next Ring: **{next_ring}**",
        "",
        "Continue the loop:",
        "```bash",
        *command_lines,
        "```",
        "",
        f"Repo: {repo_url}",
        "````",
        "",
        "## Agent Prompt",
        "```text",
        (
            f"Use CyberHuaTuo to help @{username} chase the next soul ring in "
            f"{framework_label}. Start from real GitHub issues, save only real fixes, "
            f"then generate the badge and share card."
        ),
        quest_command,
        "```",
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "Rule: this campaign pack only reports current real prescription data; no fake rank, no invented contribution history.",
    ])


def _format_duel_rank(profile: dict) -> str:
    return (
        f"#{profile['global_rank']} / {profile['global_total']}"
        if int(profile.get("contribution_count", 0)) > 0
        else "not ranked yet"
    )


def _format_duel_delta(count: int) -> str:
    return "1 real prescription" if count == 1 else f"{count} real prescriptions"


def _format_duel_user_snapshot(
    username: str,
    profile: dict,
    framework: str,
    framework_label: str,
) -> dict:
    fw_counts = count_contributor_cases_by_framework(username)
    alchemy = get_alchemy_profile(username)
    target_key = get_direction_for_framework(framework)
    target_direction = None
    for direction in alchemy.get("directions", []):
        if direction["key"] == target_key:
            target_direction = direction
            break

    if target_direction:
        ring = (
            f"{target_direction['emoji']} {target_direction['name_cn']} / "
            f"{target_direction['name_en']} · {target_direction['rings']} "
            f"{target_direction['ring_name']}"
        )
        next_ring = target_direction["next_ring"]["hint_cn"]
        framework_count = target_direction["count"]
    else:
        ring = "not lit yet / 尚未点亮魂环"
        next_ring = "first soul ring: contribute 1 real prescription / 第一魂环: 白环 · 贡献 1 方真实药方即可点亮。"
        framework_count = fw_counts.get(framework, 0)

    return {
        "username": username,
        "title": f"{profile['title_emoji']} {profile['title_cn']} / {profile['title_en']}",
        "prescriptions": int(profile.get("contribution_count", 0)),
        "prescription_text": _format_prescription_count(int(profile.get("contribution_count", 0))),
        "rank": _format_duel_rank(profile),
        "framework": framework_label,
        "framework_count": framework_count,
        "ring": ring,
        "next_ring": next_ring,
    }


def format_soul_ring_duel_card(
    challenger_github: str,
    rival_github: str,
    framework: str = "",
) -> str:
    """Generate a real-data two-player Soul Ring duel invitation card."""
    challenger = challenger_github.strip() or "your-github-username"
    rival = rival_github.strip() or "friend-github-username"
    challenger_profile = get_cultivation_profile(challenger)
    rival_profile = get_cultivation_profile(rival)
    challenger_counts = count_contributor_cases_by_framework(challenger)
    rival_counts = count_contributor_cases_by_framework(rival)
    duel_framework = framework.strip() or _select_quest_framework(
        challenger_counts if challenger_counts else rival_counts,
        "",
    )
    framework_label = _format_framework_label(duel_framework)
    challenger_snapshot = _format_duel_user_snapshot(
        challenger,
        challenger_profile,
        duel_framework,
        framework_label,
    )
    rival_snapshot = _format_duel_user_snapshot(
        rival,
        rival_profile,
        duel_framework,
        framework_label,
    )

    challenger_total = challenger_snapshot["prescriptions"]
    rival_total = rival_snapshot["prescriptions"]
    if challenger_total > rival_total:
        lead_line = f"Current Lead: @{challenger} by {_format_duel_delta(challenger_total - rival_total)}"
    elif rival_total > challenger_total:
        lead_line = f"Current Lead: @{rival} by {_format_duel_delta(rival_total - challenger_total)}"
    elif challenger_total == 0:
        lead_line = "Open Duel: first real prescription lights the first soul ring"
    else:
        lead_line = f"Tie Duel: both alchemists have {_format_prescription_count(challenger_total)}"

    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"
    challenger_quest = f"cyberhuatuo quest {challenger} --framework {duel_framework}"
    rival_quest = f"cyberhuatuo quest {rival} --framework {duel_framework}"
    challenger_challenge = f"cyberhuatuo challenge --username {challenger} --framework {duel_framework}"
    rival_challenge = f"cyberhuatuo challenge --username {rival} --framework {duel_framework}"
    challenger_campaign = f"cyberhuatuo campaign {challenger} --framework {duel_framework}"
    rival_campaign = f"cyberhuatuo campaign {rival} --framework {duel_framework}"

    return "\n".join([
        "# 🔮 Soul Ring Duel Card",
        "",
        f"- Challenger: @{challenger}",
        f"- Rival: @{rival}",
        f"- Target Framework: {framework_label} (`{duel_framework}`)",
        "- Duel Snapshot Formula: real prescription count in the current CyberHuaTuo knowledge base; rank is shown only after at least one real prescription.",
        f"- {lead_line}",
        "",
        "## Challenger Snapshot",
        f"- Alchemist: @{challenger_snapshot['username']}",
        f"- Title: {challenger_snapshot['title']}",
        f"- Prescriptions: {challenger_snapshot['prescription_text']}",
        f"- Global Rank: {challenger_snapshot['rank']}",
        f"- {framework_label} Prescriptions: {challenger_snapshot['framework_count']}",
        f"- Current Soul Ring: {challenger_snapshot['ring']}",
        f"- Next Ring: {challenger_snapshot['next_ring']}",
        "",
        "## Rival Snapshot",
        f"- Alchemist: @{rival_snapshot['username']}",
        f"- Title: {rival_snapshot['title']}",
        f"- Prescriptions: {rival_snapshot['prescription_text']}",
        f"- Global Rank: {rival_snapshot['rank']}",
        f"- {framework_label} Prescriptions: {rival_snapshot['framework_count']}",
        f"- Current Soul Ring: {rival_snapshot['ring']}",
        f"- Next Ring: {rival_snapshot['next_ring']}",
        "",
        "## X / Weibo",
        "```text",
        (
            f"@{rival} I challenge you to a CyberHuaTuo Soul Ring Duel in "
            f"{framework_label}. {lead_line}."
        ),
        f"Challenger: @{challenger} · {challenger_snapshot['prescription_text']} · Global Rank {challenger_snapshot['rank']}",
        f"Rival: @{rival} · {rival_snapshot['prescription_text']} · Global Rank {rival_snapshot['rank']}",
        f"Join: {repo_url}",
        "#CyberHuaTuo #SoulRingDuel #AIAgents",
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        f"### 🔮 Soul Ring Duel: @{challenger} vs @{rival}",
        "",
        f"**Target framework:** {framework_label} (`{duel_framework}`)",
        "**Snapshot formula:** real prescription count in the current CyberHuaTuo knowledge base.",
        f"**Status:** {lead_line}",
        "",
        "| Alchemist | Real prescriptions | Global rank | Current soul ring | Next action |",
        "|---|---:|---|---|---|",
        (
            f"| @{challenger} | {challenger_snapshot['prescription_text']} | "
            f"{challenger_snapshot['rank']} | {challenger_snapshot['ring']} | `{challenger_quest}` |"
        ),
        (
            f"| @{rival} | {rival_snapshot['prescription_text']} | "
            f"{rival_snapshot['rank']} | {rival_snapshot['ring']} | `{rival_quest}` |"
        ),
        "",
        "Start or continue the duel:",
        "```bash",
        challenger_challenge,
        rival_challenge,
        challenger_quest,
        rival_quest,
        challenger_campaign,
        rival_campaign,
        "```",
        "",
        f"Repo: {repo_url}",
        "````",
        "",
        "## Commands",
        "```bash",
        challenger_challenge,
        rival_challenge,
        challenger_quest,
        rival_quest,
        challenger_campaign,
        rival_campaign,
        "```",
        "",
        "Rule: this duel card only reports current real prescription data; no fake rank, no invented wins, no historical claims.",
    ])


def format_soul_ring_mentor_pact(
    mentor_github: str,
    apprentice_github: str,
    framework: str = "langchain",
) -> str:
    """Generate a real-data mentor-apprentice pact for first-ring onboarding."""
    mentor = mentor_github.strip() or "mentor-github"
    apprentice = apprentice_github.strip() or "apprentice-github"
    pact_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(pact_framework)
    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"

    mentor_profile = get_cultivation_profile(mentor)
    apprentice_profile = get_cultivation_profile(apprentice)
    mentor_snapshot = _format_duel_user_snapshot(
        mentor,
        mentor_profile,
        pact_framework,
        framework_label,
    )
    apprentice_snapshot = _format_duel_user_snapshot(
        apprentice,
        apprentice_profile,
        pact_framework,
        framework_label,
    )

    mentor_power = _format_prescription_count(mentor_snapshot["prescriptions"])
    apprentice_foundation = _format_prescription_count(apprentice_snapshot["prescriptions"])
    if mentor_snapshot["prescriptions"] == 0 and apprentice_snapshot["prescriptions"] == 0:
        status_line = "Open Mentor Pact: first real apprentice prescription lights the pact"
    elif apprentice_snapshot["prescriptions"] == 0:
        status_line = f"First-Ring Pact: @{mentor} guides @{apprentice} to the first real soul ring"
    else:
        status_line = f"Active Mentor Pact: @{mentor} reviews @{apprentice}'s next real prescription"

    if int(apprentice_snapshot["framework_count"]) <= 0:
        breakthrough_target = (
            f"Breakthrough Target: @{apprentice} lights first {framework_label} "
            "soul ring with 1 real prescription"
        )
    else:
        breakthrough_target = (
            f"Breakthrough Target: @{apprentice} advances the next {framework_label} "
            f"soul ring; current gate is {apprentice_snapshot['next_ring']}"
        )

    mentor_duty = "Mentor Duty: review one real prescription and publish the pact update"
    apprentice_challenge = f"cyberhuatuo challenge --username {apprentice} --framework {pact_framework}"
    apprentice_quest = f"cyberhuatuo quest {apprentice} --framework {pact_framework}"
    apprentice_upload = (
        f'cyberhuatuo upload --title "Fix real {framework_label} issue" '
        '--prescription "Record the real error, root cause, versions, and fix" '
        f"--framework {pact_framework} --contributor {apprentice}"
    )
    apprentice_ladder = f"cyberhuatuo ladder {apprentice} --framework {pact_framework}"
    apprentice_duel = f"cyberhuatuo duel {apprentice} {mentor} --framework {pact_framework}"
    apprentice_campaign = f"cyberhuatuo campaign {apprentice} --framework {pact_framework}"
    mentor_campaign = f"cyberhuatuo campaign {mentor} --framework {pact_framework}"
    command_lines = [
        apprentice_challenge,
        apprentice_quest,
        apprentice_upload,
        apprentice_ladder,
        apprentice_duel,
        apprentice_campaign,
        mentor_campaign,
    ]

    return "\n".join([
        "# Soul Ring Mentor Pact",
        "",
        f"- Mentor: @{mentor}",
        f"- Apprentice: @{apprentice}",
        f"- Target Framework: {framework_label} (`{pact_framework}`)",
        "- Pact Formula: mentor and apprentice snapshots use current real prescription counts; mentor power and apprentice foundation are not invented.",
        f"- Mentor Power: {mentor_power}",
        f"- Apprentice Foundation: {apprentice_foundation}",
        f"- {status_line}",
        f"- {breakthrough_target}",
        f"- {mentor_duty}",
        "",
        "## Mentor Snapshot",
        f"- Alchemist: @{mentor_snapshot['username']}",
        f"- Title: {mentor_snapshot['title']}",
        f"- Prescriptions: {mentor_snapshot['prescription_text']}",
        f"- Global Rank: {mentor_snapshot['rank']}",
        f"- {framework_label} Prescriptions: {mentor_snapshot['framework_count']}",
        f"- Current Soul Ring: {mentor_snapshot['ring']}",
        f"- Next Ring: {mentor_snapshot['next_ring']}",
        "",
        "## Apprentice Snapshot",
        f"- Alchemist: @{apprentice_snapshot['username']}",
        f"- Title: {apprentice_snapshot['title']}",
        f"- Prescriptions: {apprentice_snapshot['prescription_text']}",
        f"- Global Rank: {apprentice_snapshot['rank']}",
        f"- {framework_label} Prescriptions: {apprentice_snapshot['framework_count']}",
        f"- Current Soul Ring: {apprentice_snapshot['ring']}",
        f"- Next Ring: {apprentice_snapshot['next_ring']}",
        "",
        "## X / Weibo",
        "```text",
        (
            f"@{mentor} opens a CyberHuaTuo Soul Ring Mentor Pact for @{apprentice} "
            f"in {framework_label}."
        ),
        f"Mentor Power: {mentor_power}",
        f"Apprentice Foundation: {apprentice_foundation}",
        breakthrough_target,
        f"Join: {repo_url}",
        "#CyberHuaTuo #SoulRingMentor #AIAgents",
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        f"### Soul Ring Mentor Pact: @{mentor} -> @{apprentice}",
        "",
        f"**Target framework:** {framework_label} (`{pact_framework}`)",
        "**Pact Formula:** mentor and apprentice snapshots use current real prescription counts.",
        f"**Mentor Power:** {mentor_power}",
        f"**Apprentice Foundation:** {apprentice_foundation}",
        f"**Status:** {status_line}",
        f"**{breakthrough_target}**",
        f"**{mentor_duty}**",
        "",
        "| Role | Alchemist | Real prescriptions | Global rank | Current soul ring |",
        "|---|---|---:|---|---|",
        (
            f"| Mentor | @{mentor_snapshot['username']} | "
            f"{mentor_snapshot['prescription_text']} | {mentor_snapshot['rank']} | "
            f"{mentor_snapshot['ring']} |"
        ),
        (
            f"| Apprentice | @{apprentice_snapshot['username']} | "
            f"{apprentice_snapshot['prescription_text']} | {apprentice_snapshot['rank']} | "
            f"{apprentice_snapshot['ring']} |"
        ),
        "",
        "Run the pact:",
        "```bash",
        *command_lines,
        "```",
        "",
        f"Repo: {repo_url}",
        "````",
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "Rule: this mentor pact reports current real prescription data only; seniority, rank, and breakthrough progress are not invented.",
    ])


def _format_tournament_cli_value(value: str) -> str:
    return f'"{value}"' if " " in value else value


def format_soul_ring_tournament_bracket(
    participants: list[str] | tuple[str, ...] | str,
    framework: str = "langchain",
    event_name: str = "CyberHuaTuo Soul Ring Cup",
) -> str:
    """Generate a real-data multi-player Soul Ring tournament bracket."""
    tournament_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(tournament_framework)
    event = event_name.strip() or "CyberHuaTuo Soul Ring Cup"
    normalized_participants = _normalize_sect_members(participants)
    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"

    snapshots = []
    for original_index, username in enumerate(normalized_participants):
        profile = get_cultivation_profile(username)
        snapshot = _format_duel_user_snapshot(
            username,
            profile,
            tournament_framework,
            framework_label,
        )
        snapshot["original_index"] = original_index
        snapshots.append(snapshot)

    seeded = sorted(snapshots, key=lambda snapshot: (-snapshot["prescriptions"], snapshot["original_index"]))
    for seed, snapshot in enumerate(seeded, start=1):
        snapshot["seed"] = seed

    top_seed = seeded[0]
    runner_up = seeded[1] if len(seeded) > 1 else None
    if top_seed["prescriptions"] <= 0:
        champion_line = "Current Champion: not claimed yet"
        chase_line = "Open Tournament: first real prescription claims the first bracket seed"
    else:
        champion_line = (
            f"Current Champion: @{top_seed['username']} with "
            f"{_format_prescription_count(top_seed['prescriptions'])}"
        )
        if runner_up:
            gap = top_seed["prescriptions"] - runner_up["prescriptions"]
            if gap <= 0:
                chase_line = (
                    f"Next Chase: @{runner_up['username']} is tied with @{top_seed['username']}; "
                    "the next real prescription breaks the tie"
                )
            else:
                chase_line = (
                    f"Next Chase: @{runner_up['username']} needs {_format_duel_delta(gap)} "
                    f"to catch @{top_seed['username']}"
                )
        else:
            chase_line = "Next Chase: invite another real alchemist into the tournament"

    bracket_pool = seeded
    bye_line = ""
    if len(seeded) % 2 == 1 and len(seeded) > 1:
        bye = seeded[0]
        bye_line = f"Bye: @{bye['username']} waits for a real challenger"
        bracket_pool = seeded[1:]

    round_lines = []
    duel_commands = []
    for match_index in range(len(bracket_pool) // 2):
        left = bracket_pool[match_index]
        right = bracket_pool[-(match_index + 1)]
        round_lines.append(
            f"Match {match_index + 1}: #{left['seed']} @{left['username']} vs "
            f"#{right['seed']} @{right['username']}"
        )
        duel_commands.append(
            f"cyberhuatuo duel {left['username']} {right['username']} --framework {tournament_framework}"
        )

    if not round_lines:
        round_lines = ["Open Round: invite at least one more real alchemist into the bracket"]

    seed_lines = []
    discussion_rows = []
    command_lines = []
    tournament_command = (
        "cyberhuatuo tournament "
        f"{' '.join(snapshot['username'] for snapshot in seeded)} "
        f"--framework {tournament_framework} --event {_format_tournament_cli_value(event)}"
    )
    command_lines.append(tournament_command)
    command_lines.extend(duel_commands)

    for snapshot in seeded:
        username = snapshot["username"]
        challenge_command = f"cyberhuatuo challenge --username {username} --framework {tournament_framework}"
        quest_command = f"cyberhuatuo quest {username} --framework {tournament_framework}"
        ladder_command = f"cyberhuatuo ladder {username} --framework {tournament_framework}"
        campaign_command = f"cyberhuatuo campaign {username} --framework {tournament_framework}"
        if snapshot["prescriptions"] <= 0:
            command_lines.append(challenge_command)
        command_lines.extend([quest_command, ladder_command, campaign_command])
        seed_lines.extend([
            f"### Seed #{snapshot['seed']}: @{username}",
            f"- Prescriptions: {snapshot['prescription_text']}",
            f"- Global Rank: {snapshot['rank']}",
            f"- {framework_label} Prescriptions: {snapshot['framework_count']}",
            f"- Current Soul Ring: {snapshot['ring']}",
            f"- Next Ring: {snapshot['next_ring']}",
            f"- Next Action: `{quest_command}`",
            "",
        ])
        discussion_rows.append(
            f"| #{snapshot['seed']} | @{username} | {snapshot['prescription_text']} | "
            f"{snapshot['rank']} | `{quest_command}` |"
        )

    return "\n".join([
        "# Soul Ring Tournament Bracket",
        "",
        f"- Event: {event}",
        f"- Target Framework: {framework_label} (`{tournament_framework}`)",
        "- Tournament Formula: seeds use current real CyberHuaTuo prescription counts; ties keep input order; champion, byes, and bracket status are current snapshots only.",
        f"- Participants: {len(seeded)}",
        f"- {champion_line}",
        f"- {chase_line}",
        *( [f"- {bye_line}"] if bye_line else [] ),
        "",
        "## Round 1",
        *round_lines,
        "",
        "## Seeds",
        *seed_lines,
        "## X / Weibo",
        "```text",
        (
            f"{event}: CyberHuaTuo Soul Ring Tournament opens with {len(seeded)} "
            f"real GitHub alchemists seeded by current real prescription counts."
        ),
        champion_line,
        chase_line,
        f"Join the bracket: {repo_url}",
        "#CyberHuaTuo #SoulRingTournament #AIAgents",
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        f"### Soul Ring Tournament Bracket: {event}",
        "",
        "**Tournament Formula:** seeds use current real CyberHuaTuo prescription counts; ties keep input order.",
        f"**Target framework:** {framework_label} (`{tournament_framework}`)",
        f"**{champion_line}**",
        f"**{chase_line}**",
        *( [f"**{bye_line}**"] if bye_line else [] ),
        "",
        "| Seed | Alchemist | Real prescriptions | Global rank | Next action |",
        "|---:|---|---:|---|---|",
        *discussion_rows,
        "",
        "Round 1:",
        *[f"- {line}" for line in round_lines],
        "",
        "Run the tournament:",
        "```bash",
        *command_lines,
        "```",
        "",
        f"Repo: {repo_url}",
        "````",
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "Rule: this tournament bracket reports current real prescription data only; seeds, champion, byes, and progress are not invented.",
    ])


def format_soul_ring_tournament_settlement(
    participants: list[str] | tuple[str, ...] | str,
    framework: str = "langchain",
    event_name: str = "CyberHuaTuo Soul Ring Cup",
) -> str:
    """Generate a real-data settlement snapshot for a Soul Ring tournament."""
    settlement_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(settlement_framework)
    event = event_name.strip() or "CyberHuaTuo Soul Ring Cup"
    normalized_participants = _normalize_sect_members(participants)
    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"

    snapshots = []
    for original_index, username in enumerate(normalized_participants):
        profile = get_cultivation_profile(username)
        snapshot = _format_duel_user_snapshot(
            username,
            profile,
            settlement_framework,
            framework_label,
        )
        snapshot["original_index"] = original_index
        snapshots.append(snapshot)

    ranked = sorted(snapshots, key=lambda snapshot: (-snapshot["prescriptions"], snapshot["original_index"]))
    for rank, snapshot in enumerate(ranked, start=1):
        snapshot["settlement_rank"] = rank

    victor = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None
    duel_command = ""
    if victor["prescriptions"] <= 0:
        victor_line = "Current Victor: not claimed yet"
        runner_line = "Runner-Up: not claimed yet"
        result_line = "Settlement Pending: first real prescription claims the settlement"
        next_hook = "Next Round Hook: every participant starts with the first real prescription"
    else:
        victor_line = (
            f"Current Victor: @{victor['username']} with "
            f"{_format_prescription_count(victor['prescriptions'])}"
        )
        if runner_up:
            runner_line = (
                f"Runner-Up: @{runner_up['username']} with "
                f"{_format_prescription_count(runner_up['prescriptions'])}"
            )
            gap = victor["prescriptions"] - runner_up["prescriptions"]
            if gap <= 0:
                result_line = (
                    f"Tie Settlement: @{victor['username']} and @{runner_up['username']} "
                    f"both have {_format_prescription_count(victor['prescriptions'])}"
                )
                next_hook = (
                    f"Next Round Hook: @{runner_up['username']} challenges "
                    f"@{victor['username']} to break the tie with the next real prescription"
                )
            else:
                result_line = (
                    f"Victory Gap: @{victor['username']} leads @{runner_up['username']} "
                    f"by {_format_duel_delta(gap)}"
                )
                next_hook = (
                    f"Next Round Hook: @{runner_up['username']} challenges "
                    f"@{victor['username']} for the next real prescription swing"
                )
            duel_command = (
                f"cyberhuatuo duel {runner_up['username']} {victor['username']} "
                f"--framework {settlement_framework}"
            )
        else:
            runner_line = "Runner-Up: invite another real alchemist"
            result_line = "Solo Settlement: one ranked participant is visible in the current snapshot"
            next_hook = "Next Round Hook: invite another real alchemist into the next bracket"

    tournament_command = (
        "cyberhuatuo tournament "
        f"{' '.join(normalized_participants)} "
        f"--framework {settlement_framework} --event {_format_tournament_cli_value(event)}"
    )
    settle_command = (
        "cyberhuatuo tournament-settle "
        f"{' '.join(normalized_participants)} "
        f"--framework {settlement_framework} --event {_format_tournament_cli_value(event)}"
    )
    command_lines = [settle_command, tournament_command]
    if duel_command:
        command_lines.append(duel_command)

    ranking_lines = []
    discussion_rows = []
    for snapshot in ranked:
        username = snapshot["username"]
        challenge_command = f"cyberhuatuo challenge --username {username} --framework {settlement_framework}"
        quest_command = f"cyberhuatuo quest {username} --framework {settlement_framework}"
        ladder_command = f"cyberhuatuo ladder {username} --framework {settlement_framework}"
        campaign_command = f"cyberhuatuo campaign {username} --framework {settlement_framework}"
        if snapshot["prescriptions"] <= 0:
            command_lines.append(challenge_command)
        command_lines.extend([quest_command, ladder_command, campaign_command])
        ranking_lines.extend([
            f"### #{snapshot['settlement_rank']} @{username}",
            f"- Prescriptions: {snapshot['prescription_text']}",
            f"- Global Rank: {snapshot['rank']}",
            f"- {framework_label} Prescriptions: {snapshot['framework_count']}",
            f"- Current Soul Ring: {snapshot['ring']}",
            f"- Next Ring: {snapshot['next_ring']}",
            f"- Continue: `{quest_command}`",
            "",
        ])
        discussion_rows.append(
            f"| #{snapshot['settlement_rank']} | @{username} | "
            f"{snapshot['prescription_text']} | {snapshot['rank']} | `{quest_command}` |"
        )

    return "\n".join([
        "# Soul Ring Tournament Settlement",
        "",
        f"- Event: {event}",
        f"- Target Framework: {framework_label} (`{settlement_framework}`)",
        "- Settlement Formula: current real CyberHuaTuo prescription counts; no bracket wins, champion history, or round progress are invented.",
        f"- Participants: {len(ranked)}",
        f"- {victor_line}",
        f"- {runner_line}",
        f"- {result_line}",
        f"- {next_hook}",
        "",
        "## Current Results",
        *ranking_lines,
        "## X / Weibo",
        "```text",
        f"{event}: CyberHuaTuo Soul Ring Tournament settlement snapshot.",
        victor_line,
        result_line,
        next_hook,
        f"Join the next round: {repo_url}",
        "#CyberHuaTuo #SoulRingTournament #AIAgents",
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        f"### Soul Ring Tournament Settlement: {event}",
        "",
        "**Settlement Formula:** current real CyberHuaTuo prescription counts only.",
        f"**Target framework:** {framework_label} (`{settlement_framework}`)",
        f"**{victor_line}**",
        f"**{runner_line}**",
        f"**{result_line}**",
        f"**{next_hook}**",
        "",
        "| Rank | Alchemist | Real prescriptions | Global rank | Next action |",
        "|---:|---|---:|---|---|",
        *discussion_rows,
        "",
        "Run the settlement and next round:",
        "```bash",
        *command_lines,
        "```",
        "",
        f"Repo: {repo_url}",
        "````",
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "Rule: this tournament settlement reports current real prescription data only; winners, rounds, champion history, and progress are not invented.",
    ])


def format_soul_ring_arena_snapshot(
    github_username: str = "",
    top_n: int = 10,
    framework: str = "langchain",
) -> str:
    """Generate a real-data leaderboard snapshot with chase and share commands."""
    username = github_username.strip() or "your-github-username"
    arena_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(arena_framework)
    stats = {
        str(user).lower(): int(count)
        for user, count in get_global_ranking_stats().items()
        if int(count) > 0
    }
    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"
    challenge_command = f"cyberhuatuo challenge --username {username} --framework {arena_framework}"
    quest_command = f"cyberhuatuo quest {username} --framework {arena_framework}"
    campaign_command = f"cyberhuatuo campaign {username} --framework {arena_framework}"

    if not stats:
        return "\n".join([
            "# 🔮 Soul Ring Arena Snapshot",
            "",
            "- Arena Snapshot Formula: real prescription count in the current CyberHuaTuo knowledge base.",
            "- Arena is empty: no ranked alchemist has a real prescription yet.",
            f"- Alchemist: @{username}",
            "- Global Rank: not ranked yet",
            f"- Target Framework: {framework_label} (`{arena_framework}`)",
            "",
            "## First Move",
            "```bash",
            challenge_command,
            quest_command,
            campaign_command,
            "```",
            "",
            "Rule: this arena snapshot only reports current real prescription data; no fake rank, no invented season history.",
        ])

    sorted_stats = sorted(stats.items(), key=lambda item: (-item[1], item[0]))
    total = len(sorted_stats)
    display_count = max(1, min(int(top_n), total))
    top_rows = sorted_stats[:display_count]
    username_key = username.lower()

    user_rank = 0
    user_count = 0
    for index, (user, count) in enumerate(sorted_stats, start=1):
        if user == username_key:
            user_rank = index
            user_count = count
            break

    if user_rank:
        position_line = f"Your Position: #{user_rank} / {total} · {_format_prescription_count(user_count)}"
        if user_rank == 1:
            rival_line = "Next Rival: no higher-ranked rival; defend the arena lead"
            rival_username = ""
        else:
            rival_username = sorted_stats[user_rank - 2][0]
            rival_line = f"Next Rival: @{rival_username}"
    else:
        position_line = "Your Position: not ranked yet"
        rival_username = sorted_stats[0][0]
        rival_line = f"Next Rival: @{rival_username}"

    duel_command = (
        f"cyberhuatuo duel {username} {rival_username} --framework {arena_framework}"
        if rival_username
        else ""
    )
    command_lines = []
    if not user_rank:
        command_lines.append(challenge_command)
    command_lines.extend([quest_command, campaign_command])
    if duel_command:
        command_lines.append(duel_command)

    top_lines = [
        f"#{rank} @{user} · {_format_prescription_count(count)}"
        for rank, (user, count) in enumerate(top_rows, start=1)
    ]

    discussion_rows = [
        f"| #{rank} | @{user} | {_format_prescription_count(count)} |"
        for rank, (user, count) in enumerate(top_rows, start=1)
    ]

    return "\n".join([
        "# 🔮 Soul Ring Arena Snapshot",
        "",
        "- Arena Snapshot Formula: real prescription count in the current CyberHuaTuo knowledge base.",
        f"- Target Framework: {framework_label} (`{arena_framework}`)",
        f"- Top {display_count}",
        f"- {position_line}",
        f"- {rival_line}",
        "",
        f"## Top {display_count}",
        *top_lines,
        "",
        "## X / Weibo",
        "```text",
        (
            f"CyberHuaTuo Soul Ring Arena snapshot: Top {display_count} real alchemists, "
            f"ranked by current real prescription count."
        ),
        position_line,
        rival_line,
        f"Join the arena: {repo_url}",
        "#CyberHuaTuo #SoulRingArena #AIAgents",
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        "### 🔮 CyberHuaTuo Soul Ring Arena Snapshot",
        "",
        "**Arena Snapshot Formula:** real prescription count in the current CyberHuaTuo knowledge base.",
        f"**Target framework:** {framework_label} (`{arena_framework}`)",
        "",
        "| Rank | Alchemist | Real prescriptions |",
        "|---:|---|---:|",
        *discussion_rows,
        "",
        f"**{position_line}**",
        f"**{rival_line}**",
        "",
        "Continue the chase:",
        "```bash",
        *command_lines,
        "```",
        "",
        f"Repo: {repo_url}",
        "````",
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "Rule: this arena snapshot only reports current real prescription data; no fake rank, no invented season history.",
    ])


def format_soul_ring_season_board(
    framework: str = "langchain",
    top_n: int = 10,
) -> str:
    """Generate a real-data season board from the current leaderboard snapshot."""
    season_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(season_framework)
    stats = {
        str(user).lower(): int(count)
        for user, count in get_global_ranking_stats().items()
        if int(count) > 0
    }
    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"

    if not stats:
        challenge_command = (
            "cyberhuatuo challenge --username your-github-username "
            f"--framework {season_framework}"
        )
        mission_command = (
            "cyberhuatuo mission --username your-github-username "
            f"--framework {season_framework}"
        )
        ladder_command = (
            "cyberhuatuo ladder your-github-username "
            f"--framework {season_framework}"
        )

        return "\n".join([
            "# Soul Ring Season Board",
            "",
            (
                "- Season Snapshot Formula: current real prescription count "
                "in the CyberHuaTuo knowledge base; no season history is invented."
            ),
            f"- Target Framework: {framework_label} (`{season_framework}`)",
            "- Season board is empty: no ranked alchemist has a real prescription yet.",
            "- Champion: not claimed yet",
            "",
            "## First Season Moves",
            "```bash",
            challenge_command,
            mission_command,
            ladder_command,
            "```",
            "",
            "## GitHub Discussion / PR Comment",
            "````markdown",
            "### Soul Ring Season Board",
            "",
            "Champion: not claimed yet.",
            "The first real prescription opens the season board.",
            "",
            "```bash",
            challenge_command,
            mission_command,
            "```",
            "",
            f"Repo: {repo_url}",
            "````",
            "",
            "Rule: this season board reports current real prescription data only; ranks, champions, and progress are not invented.",
        ])

    sorted_stats = sorted(stats.items(), key=lambda item: (-item[1], item[0]))
    display_count = max(1, min(int(top_n), len(sorted_stats)))
    top_rows = sorted_stats[:display_count]
    champion_username, champion_count = top_rows[0]
    runner_up = top_rows[1] if len(top_rows) > 1 else None

    leaderboard_lines = [
        f"#{rank} @{user} - {_format_prescription_count(count)}"
        for rank, (user, count) in enumerate(top_rows, start=1)
    ]
    discussion_rows = [
        (
            f"| #{rank} | @{user} | {_format_prescription_count(count)} | "
            f"`cyberhuatuo quest {user} --framework {season_framework}` |"
        )
        for rank, (user, count) in enumerate(top_rows, start=1)
    ]

    champion_line = (
        f"Champion: @{champion_username} with "
        f"{_format_prescription_count(champion_count)}"
    )
    if runner_up:
        runner_up_username = runner_up[0]
        chase_line = f"Next Chase: @{runner_up_username} challenges @{champion_username}"
        duel_command = (
            f"cyberhuatuo duel {runner_up_username} {champion_username} "
            f"--framework {season_framework}"
        )
    else:
        chase_line = "Next Chase: invite the next real alchemist into the season"
        duel_command = ""

    arena_command = (
        f"cyberhuatuo arena {champion_username} --top-n {display_count} "
        f"--framework {season_framework}"
    )
    quest_command = f"cyberhuatuo quest {champion_username} --framework {season_framework}"
    campaign_command = (
        f"cyberhuatuo campaign {champion_username} --framework {season_framework}"
    )
    ladder_command = f"cyberhuatuo ladder {champion_username} --framework {season_framework}"
    command_lines = [arena_command]
    if duel_command:
        command_lines.append(duel_command)
    command_lines.extend([quest_command, campaign_command, ladder_command])

    return "\n".join([
        "# Soul Ring Season Board",
        "",
        (
            "- Season Snapshot Formula: current real prescription count "
            "in the CyberHuaTuo knowledge base; no season history is invented."
        ),
        f"- Target Framework: {framework_label} (`{season_framework}`)",
        f"- Top {display_count}",
        f"- {champion_line}",
        f"- {chase_line}",
        "",
        f"## Top {display_count}",
        *leaderboard_lines,
        "",
        "## X / Weibo",
        "```text",
        (
            f"CyberHuaTuo Soul Ring Season Board: Top {display_count} "
            "real alchemists ranked by current real prescription count."
        ),
        champion_line,
        chase_line,
        f"Join the season: {repo_url}",
        "#CyberHuaTuo #SoulRingSeason #AIAgents",
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        "### Soul Ring Season Board",
        "",
        (
            "**Season Snapshot Formula:** current real prescription count "
            "in the CyberHuaTuo knowledge base."
        ),
        f"**Target framework:** {framework_label} (`{season_framework}`)",
        "",
        "| Rank | Alchemist | Real prescriptions | Next action |",
        "|---:|---|---:|---|",
        *discussion_rows,
        "",
        f"**{champion_line}**",
        f"**{chase_line}**",
        "",
        "Continue the season:",
        "```bash",
        *command_lines,
        "```",
        "",
        f"Repo: {repo_url}",
        "````",
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "Rule: this season board reports current real prescription data only; ranks, champions, and progress are not invented.",
    ])


def _normalize_sect_members(members: list[str] | tuple[str, ...] | str) -> list[str]:
    if isinstance(members, str):
        raw_members = members.replace(",", " ").split()
    else:
        raw_members = []
        for member in members:
            raw_members.extend(str(member).replace(",", " ").split())

    normalized = []
    seen = set()
    for member in raw_members:
        username = member.strip().lstrip("@")
        key = username.lower()
        if username and key not in seen:
            seen.add(key)
            normalized.append(username)

    return normalized or ["your-github-username"]


def format_soul_ring_sect_card(
    sect_name: str,
    members: list[str] | tuple[str, ...] | str,
    framework: str = "langchain",
) -> str:
    """Generate a real-data multi-member Soul Ring sect/team card."""
    name = sect_name.strip() or "CyberHuaTuo Sect"
    sect_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(sect_framework)
    normalized_members = _normalize_sect_members(members)
    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"

    snapshots = []
    for member in normalized_members:
        profile = get_cultivation_profile(member)
        snapshots.append(_format_duel_user_snapshot(member, profile, sect_framework, framework_label))

    sect_power = sum(snapshot["prescriptions"] for snapshot in snapshots)
    sect_power_text = _format_duel_delta(sect_power)
    if sect_power > 0:
        leader_index, leader = max(
            enumerate(snapshots),
            key=lambda item: (item[1]["prescriptions"], -item[0]),
        )
        status_line = (
            f"Leading Member: @{leader['username']} with "
            f"{_format_duel_delta(leader['prescriptions'])}"
        )
    else:
        leader_index = 0
        leader = snapshots[0]
        status_line = "Sect is unranked: first real prescription lights the sect banner"

    member_lines = []
    for snapshot in snapshots:
        member_lines.extend([
            f"### @{snapshot['username']}",
            f"- Title: {snapshot['title']}",
            f"- Prescriptions: {snapshot['prescription_text']}",
            f"- Global Rank: {snapshot['rank']}",
            f"- {framework_label} Prescriptions: {snapshot['framework_count']}",
            f"- Current Soul Ring: {snapshot['ring']}",
            f"- Next Ring: {snapshot['next_ring']}",
            "",
        ])

    discussion_rows = [
        (
            f"| @{snapshot['username']} | {snapshot['prescription_text']} | "
            f"{snapshot['rank']} | {snapshot['ring']} | "
            f"`cyberhuatuo quest {snapshot['username']} --framework {sect_framework}` |"
        )
        for snapshot in snapshots
    ]

    command_lines = []
    for snapshot in snapshots:
        username = snapshot["username"]
        command_lines.extend([
            f"cyberhuatuo challenge --username {username} --framework {sect_framework}",
            f"cyberhuatuo quest {username} --framework {sect_framework}",
            f"cyberhuatuo campaign {username} --framework {sect_framework}",
        ])

    anchor_member = snapshots[leader_index]["username"] if sect_power > 0 else snapshots[0]["username"]
    arena_command = f"cyberhuatuo arena {anchor_member} --top-n 10 --framework {sect_framework}"
    duel_command = (
        f"cyberhuatuo duel {snapshots[0]['username']} {snapshots[1]['username']} --framework {sect_framework}"
        if len(snapshots) >= 2
        else ""
    )
    command_lines.append(arena_command)
    if duel_command:
        command_lines.append(duel_command)

    member_handles = ", ".join(f"@{snapshot['username']}" for snapshot in snapshots)

    return "\n".join([
        "# Soul Ring Sect Card",
        "",
        f"- Sect: {name}",
        f"- Members: {member_handles}",
        f"- Target Framework: {framework_label} (`{sect_framework}`)",
        "- Sect Power Formula: sum of current real prescription counts from listed GitHub members.",
        f"- Sect Power: {sect_power_text}",
        f"- {status_line}",
        "",
        "## Members",
        *member_lines,
        "## Recruitment Post",
        "```text",
        (
            f"{name} is recruiting real CyberHuaTuo contributors for {framework_label}. "
            f"Sect Power: {sect_power_text}. {status_line}."
        ),
        f"Members: {member_handles}",
        f"Join the sect by submitting a real prescription: {repo_url}",
        "#CyberHuaTuo #SoulRingSect #AIAgents",
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        f"### Soul Ring Sect: {name}",
        "",
        f"**Target framework:** {framework_label} (`{sect_framework}`)",
        "**Sect Power Formula:** sum of current real prescription counts from listed GitHub members.",
        f"**Sect Power:** {sect_power_text}",
        f"**Status:** {status_line}",
        "",
        "| Member | Real prescriptions | Global rank | Current soul ring | Next action |",
        "|---|---:|---|---|---|",
        *discussion_rows,
        "",
        "Join or level up the sect:",
        "```bash",
        *command_lines,
        "```",
        "",
        f"Repo: {repo_url}",
        "````",
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "Rule: this sect card only reports current real prescription data; no fake rank, no invented sect history.",
    ])


def format_soul_ring_sect_recruitment_scroll(
    sect_name: str,
    members: list[str] | tuple[str, ...] | str,
    invitee: str = "new-member-github",
    framework: str = "langchain",
) -> str:
    """Generate a real-data invitation artifact for recruiting one sect member."""
    name = sect_name.strip() or "CyberHuaTuo Sect"
    recruit_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(recruit_framework)
    normalized_members = _normalize_sect_members(members)
    invitee_username = invitee.strip().lstrip("@") or "new-member-github"
    is_placeholder = invitee_username == "new-member-github"
    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"

    member_snapshots = []
    for member in normalized_members:
        profile = get_cultivation_profile(member)
        member_snapshots.append(
            _format_duel_user_snapshot(member, profile, recruit_framework, framework_label)
        )

    sect_power = sum(snapshot["prescriptions"] for snapshot in member_snapshots)
    sect_power_text = _format_duel_delta(sect_power)
    command_name = _format_sect_command_name(name)
    member_args = " ".join(snapshot["username"] for snapshot in member_snapshots)
    joined_member_args = f"{member_args} {invitee_username}".strip()
    member_handles = ", ".join(f"@{snapshot['username']}" for snapshot in member_snapshots)
    invitee_handle = (
        f"@{invitee_username} (placeholder)" if is_placeholder else f"@{invitee_username}"
    )

    if is_placeholder:
        candidate_line = (
            f"Candidate Snapshot: @{invitee_username} is an explicit placeholder; "
            "no contribution lookup is performed."
        )
        candidate_rank_line = "Candidate Global Rank: replace placeholder before posting"
        placeholder_note = "Replace `new-member-github` with a real GitHub username before posting."
        candidate_prescriptions = 0
    else:
        candidate_profile = get_cultivation_profile(invitee_username)
        candidate_snapshot = _format_duel_user_snapshot(
            invitee_username,
            candidate_profile,
            recruit_framework,
            framework_label,
        )
        candidate_prescriptions = int(candidate_snapshot["prescriptions"])
        candidate_line = (
            f"Candidate Snapshot: @{candidate_snapshot['username']} has "
            f"{_format_prescription_count(candidate_prescriptions)}"
        )
        candidate_rank_line = f"Candidate Global Rank: {candidate_snapshot['rank']}"
        placeholder_note = ""

    admission_trial = f"Admission Trial: fix one real {framework_label} issue"
    join_command = (
        f"cyberhuatuo sect {command_name} {joined_member_args} --framework {recruit_framework}"
    )
    sect_quest_command = (
        f"cyberhuatuo sect-quest {command_name} {joined_member_args} --framework {recruit_framework}"
    )
    sect_hall_command = (
        f"cyberhuatuo sect-hall {command_name} {joined_member_args} --framework {recruit_framework}"
    )
    candidate_challenge_command = (
        f"cyberhuatuo challenge --username {invitee_username} --framework {recruit_framework}"
    )
    candidate_quest_command = (
        f"cyberhuatuo quest {invitee_username} --framework {recruit_framework}"
    )
    candidate_campaign_command = (
        f"cyberhuatuo campaign {invitee_username} --framework {recruit_framework}"
    )
    upload_command = (
        f'cyberhuatuo upload --title "Fix real {framework_label} issue" '
        '--prescription "Record the real error, root cause, versions, and fix" '
        f"--framework {recruit_framework} --contributor {invitee_username}"
    )

    member_rows = [
        (
            f"| @{snapshot['username']} | {snapshot['prescription_text']} | "
            f"{snapshot['rank']} | {snapshot['ring']} |"
        )
        for snapshot in member_snapshots
    ]
    command_lines = [
        join_command,
        sect_quest_command,
        sect_hall_command,
        candidate_challenge_command,
        candidate_quest_command,
        upload_command,
        candidate_campaign_command,
    ]

    optional_note_lines = [f"- {placeholder_note}", ""] if placeholder_note else []

    return "\n".join([
        "# Soul Ring Sect Recruitment Scroll",
        "",
        f"- Sect: {name}",
        f"- Current Members: {member_handles}",
        f"- Invitee: {invitee_handle}",
        f"- Target Framework: {framework_label} (`{recruit_framework}`)",
        "- Recruitment Formula: current sect power is the sum of current real prescription counts from listed members.",
        f"- Current Sect Power: {sect_power_text}",
        f"- {candidate_line}",
        f"- {candidate_rank_line}",
        f"- {admission_trial}",
        f"- Join Command: {join_command}",
        *optional_note_lines,
        "## Current Sect Members",
        "| Member | Real prescriptions | Global rank | Current soul ring |",
        "|---|---:|---|---|",
        *member_rows,
        "",
        "## X / Weibo",
        "```text",
        (
            f"{name} invites {invitee_handle} into the CyberHuaTuo Soul Ring Sect. "
            f"Current sect power: {sect_power_text}."
        ),
        candidate_line,
        admission_trial,
        f"Join: {repo_url}",
        "#CyberHuaTuo #SoulRingSect #AIAgents",
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        f"### Soul Ring Sect Recruitment Scroll: {name}",
        "",
        f"**Invitee:** {invitee_handle}",
        f"**Target framework:** {framework_label} (`{recruit_framework}`)",
        "**Recruitment Formula:** current sect power is the sum of current real prescription counts from listed members.",
        f"**Current Sect Power:** {sect_power_text}",
        f"**Candidate:** {candidate_line}",
        f"**Trial:** {admission_trial}",
        "",
        "| Member | Real prescriptions | Global rank | Current soul ring |",
        "|---|---:|---|---|",
        *member_rows,
        "",
        "Accept or update the invitation:",
        "```bash",
        *command_lines,
        "```",
        "",
        f"Repo: {repo_url}",
        "````",
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "Rule: this recruitment scroll reports current real prescription data only; membership, rank, and progress are not invented.",
    ])


def format_soul_ring_sect_quest_board(
    sect_name: str,
    members: list[str] | tuple[str, ...] | str,
    framework: str = "langchain",
) -> str:
    """Generate a real-data quest board for a Soul Ring sect/team."""
    name = sect_name.strip() or "CyberHuaTuo Sect"
    sect_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(sect_framework)
    normalized_members = _normalize_sect_members(members)
    repo_display, mine_command = _format_quest_repo_line(sect_framework)
    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"

    snapshots = []
    for member in normalized_members:
        profile = get_cultivation_profile(member)
        snapshots.append(_format_duel_user_snapshot(member, profile, sect_framework, framework_label))

    sect_power = sum(snapshot["prescriptions"] for snapshot in snapshots)
    sect_power_text = _format_duel_delta(sect_power)
    _, priority = min(
        enumerate(snapshots),
        key=lambda item: (item[1]["prescriptions"], item[0]),
    )
    if sect_power == 0:
        objective_line = "Sect Objective: first real prescription lights the sect banner"
    else:
        objective_line = (
            "Sect Objective: every member contributes one real prescription "
            "toward the next shared banner"
        )

    member_handles = ", ".join(f"@{snapshot['username']}" for snapshot in snapshots)
    sect_card_command = (
        f"cyberhuatuo sect {name.replace(' ', '-')} "
        f"{' '.join(snapshot['username'] for snapshot in snapshots)} --framework {sect_framework}"
    )
    sect_quest_command = (
        f"cyberhuatuo sect-quest {name.replace(' ', '-')} "
        f"{' '.join(snapshot['username'] for snapshot in snapshots)} --framework {sect_framework}"
    )

    member_lines = []
    command_lines = [mine_command]
    discussion_rows = []
    for snapshot in snapshots:
        username = snapshot["username"]
        challenge_command = f"cyberhuatuo challenge --username {username} --framework {sect_framework}"
        quest_command = f"cyberhuatuo quest {username} --framework {sect_framework}"
        upload_command = (
            f'cyberhuatuo upload --title "Fix real {framework_label} issue" '
            '--prescription "Record the real error, root cause, versions, and fix" '
            f"--framework {sect_framework} --contributor {username}"
        )
        campaign_command = f"cyberhuatuo campaign {username} --framework {sect_framework}"

        member_lines.extend([
            f"### @{username}",
            f"- Prescriptions: {snapshot['prescription_text']}",
            f"- Global Rank: {snapshot['rank']}",
            f"- Current Soul Ring: {snapshot['ring']}",
            f"- Next Ring: {snapshot['next_ring']}",
            f"- Assignment: refine one real {framework_label} issue into a CyberHuaTuo prescription.",
            "```bash",
            challenge_command,
            quest_command,
            upload_command,
            campaign_command,
            "```",
            "",
        ])
        command_lines.extend([challenge_command, quest_command, upload_command, campaign_command])
        discussion_rows.append(
            f"| @{username} | {snapshot['prescription_text']} | {snapshot['rank']} | "
            f"`{quest_command}` | `{upload_command}` |"
        )

    command_lines.extend([sect_card_command, sect_quest_command])

    return "\n".join([
        "# Soul Ring Sect Quest Board",
        "",
        f"- Sect: {name}",
        f"- Members: {member_handles}",
        f"- Target Framework: {framework_label} (`{sect_framework}`)",
        f"- Target Repo: {repo_display}",
        "- Sect Quest Formula: per-member next actions from current real prescription counts; sect power is the sum of current real prescription counts.",
        f"- Sect Power: {sect_power_text}",
        f"- {objective_line}",
        f"- Priority Member: @{priority['username']}",
        "",
        "## Target Repository",
        "```bash",
        mine_command,
        "```",
        "",
        "## Member Assignments",
        *member_lines,
        "## Sect Rally Post",
        "```text",
        (
            f"{name} quest board is open for {framework_label}. "
            f"Sect Power: {sect_power_text}. Priority member: @{priority['username']}."
        ),
        objective_line,
        f"Members: {member_handles}",
        f"Join: {repo_url}",
        "#CyberHuaTuo #SoulRingSect #AIAgents",
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        f"### Soul Ring Sect Quest Board: {name}",
        "",
        f"**Target framework:** {framework_label} (`{sect_framework}`)",
        f"**Target repo:** {repo_display}",
        "**Sect Quest Formula:** per-member next actions from current real prescription counts.",
        f"**Sect Power:** {sect_power_text}",
        f"**Priority Member:** @{priority['username']}",
        "",
        "| Member | Real prescriptions | Global rank | Quest | Upload proof |",
        "|---|---:|---|---|---|",
        *discussion_rows,
        "",
        "Run the sect board:",
        "```bash",
        *command_lines,
        "```",
        "",
        f"Repo: {repo_url}",
        "````",
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "Rule: this sect quest board only reports current real prescription data and real target repositories; no fake rank, no invented sect progress.",
    ])


SECT_HALL_POSTS = (
    {"name": "Outer Disciple", "threshold": 0},
    {"name": "Inner Disciple", "threshold": 1},
    {"name": "Core Disciple", "threshold": 3},
    {"name": "Hall Deacon", "threshold": 5},
    {"name": "Sect Elder", "threshold": 10},
)


def _get_sect_hall_post(prescriptions: int) -> dict:
    current = SECT_HALL_POSTS[0]
    for post in SECT_HALL_POSTS:
        if prescriptions >= post["threshold"]:
            current = post
    return current


def _format_sect_hall_next_gate(prescriptions: int) -> str:
    for post in SECT_HALL_POSTS:
        if prescriptions < post["threshold"]:
            return f"{post['name']} needs {_format_duel_delta(post['threshold'] - prescriptions)}"
    return "Highest public sect post reached"


def format_soul_ring_sect_hall(
    sect_name: str,
    members: list[str] | tuple[str, ...] | str,
    framework: str = "langchain",
) -> str:
    """Generate a real-data hierarchy snapshot for a Soul Ring sect/team."""
    name = sect_name.strip() or "CyberHuaTuo Sect"
    hall_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(hall_framework)
    normalized_members = _normalize_sect_members(members)
    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"

    snapshots = []
    for member in normalized_members:
        profile = get_cultivation_profile(member)
        snapshot = _format_duel_user_snapshot(member, profile, hall_framework, framework_label)
        snapshot["sect_post"] = _get_sect_hall_post(snapshot["prescriptions"])
        snapshot["next_gate"] = _format_sect_hall_next_gate(snapshot["prescriptions"])
        snapshots.append(snapshot)

    sect_power = sum(snapshot["prescriptions"] for snapshot in snapshots)
    sect_power_text = _format_duel_delta(sect_power)
    _, senior = max(enumerate(snapshots), key=lambda item: (item[1]["prescriptions"], -item[0]))
    _, priority = min(enumerate(snapshots), key=lambda item: (item[1]["prescriptions"], item[0]))

    if sect_power == 0:
        status_line = "Sect Hall is open: first real prescription promotes an Outer Disciple to Inner Disciple"
    else:
        status_line = f"Senior Member: @{senior['username']}"

    command_name = _format_sect_command_name(name)
    member_args = " ".join(snapshot["username"] for snapshot in snapshots)
    member_handles = ", ".join(f"@{snapshot['username']}" for snapshot in snapshots)
    hierarchy_text = "Outer Disciple -> Inner Disciple -> Core Disciple -> Hall Deacon -> Sect Elder"
    sect_hall_command = f"cyberhuatuo sect-hall {command_name} {member_args} --framework {hall_framework}"
    sect_card_command = f"cyberhuatuo sect {command_name} {member_args} --framework {hall_framework}"
    sect_quest_command = f"cyberhuatuo sect-quest {command_name} {member_args} --framework {hall_framework}"
    sect_arena_command = f"cyberhuatuo sect-arena --sect {command_name} {member_args} --framework {hall_framework}"

    roster_rows = []
    member_lines = []
    command_lines = [sect_hall_command, sect_card_command, sect_quest_command, sect_arena_command]
    for snapshot in snapshots:
        username = snapshot["username"]
        post_name = snapshot["sect_post"]["name"]
        challenge_command = f"cyberhuatuo challenge --username {username} --framework {hall_framework}"
        quest_command = f"cyberhuatuo quest {username} --framework {hall_framework}"
        campaign_command = f"cyberhuatuo campaign {username} --framework {hall_framework}"
        real_prescriptions = _format_duel_delta(snapshot["prescriptions"])
        command_lines.extend([challenge_command, quest_command, campaign_command])
        roster_rows.append(
            f"| @{username} | {post_name} | {real_prescriptions} | {snapshot['next_gate']} |"
        )
        member_lines.extend([
            f"### @{username}",
            f"- Sect Post: {post_name}",
            f"- Prescriptions: {snapshot['prescription_text']}",
            f"- Global Rank: {snapshot['rank']}",
            f"- Current Soul Ring: {snapshot['ring']}",
            f"- Next Gate: {snapshot['next_gate']}",
            "```bash",
            challenge_command,
            quest_command,
            campaign_command,
            "```",
            "",
        ])

    return "\n".join([
        "# Soul Ring Sect Hall",
        "",
        f"- Sect: {name}",
        f"- Members: {member_handles}",
        f"- Target Framework: {framework_label} (`{hall_framework}`)",
        "- Sect Hall Formula: member posts are assigned from current real prescription counts; sect power is the sum of current real prescription counts.",
        f"- Sect Hierarchy: {hierarchy_text}",
        f"- Sect Power: {sect_power_text}",
        f"- {status_line}",
        f"- Admission Priority: @{priority['username']}",
        "",
        "## Hall Roster",
        "| Member | Sect post | Real prescriptions | Next gate |",
        "|---|---|---:|---|",
        *roster_rows,
        "",
        "## Member Gates",
        *member_lines,
        "## X / Weibo",
        "```text",
        (
            f"{name} opens a CyberHuaTuo Soul Ring Sect Hall for {framework_label}. "
            f"Sect Power: {sect_power_text}. {status_line}."
        ),
        f"Hierarchy: {hierarchy_text}",
        f"Admission Priority: @{priority['username']}",
        f"Join: {repo_url}",
        "#CyberHuaTuo #SoulRingSectHall #AIAgents",
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        f"### Soul Ring Sect Hall: {name}",
        "",
        f"**Target framework:** {framework_label} (`{hall_framework}`)",
        "**Sect Hall Formula:** member posts are assigned from current real prescription counts.",
        f"**Sect Hierarchy:** {hierarchy_text}",
        f"**Sect Power:** {sect_power_text}",
        f"**Status:** {status_line}",
        f"**Admission Priority:** @{priority['username']}",
        "",
        "| Member | Sect post | Real prescriptions | Next gate |",
        "|---|---|---:|---|",
        *roster_rows,
        "",
        "Open or update the sect hall:",
        "```bash",
        *command_lines,
        "```",
        "",
        f"Repo: {repo_url}",
        "````",
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "Rule: this sect hall only reports current real prescription data; no invented posts, no invented sect history.",
    ])


def _format_sect_command_name(sect_name: str) -> str:
    return sect_name.strip().replace(" ", "-") or "CyberHuaTuo-Sect"


def _parse_sect_spec_string(spec: str) -> tuple[str, list[str]] | None:
    clean_spec = spec.strip()
    if not clean_spec:
        return None

    if ":" in clean_spec:
        name, members = clean_spec.split(":", 1)
        return name.strip() or "CyberHuaTuo Sect", _normalize_sect_members(members)

    values = clean_spec.replace(",", " ").split()
    if not values:
        return None
    return values[0], _normalize_sect_members(values[1:])


def _normalize_sect_specs(
    sects: list[tuple[str, list[str] | tuple[str, ...] | str]] | list[list[str]] | tuple | str,
) -> list[tuple[str, list[str]]]:
    raw_specs = [part for part in sects.split(";") if part.strip()] if isinstance(sects, str) else list(sects)

    normalized_specs = []
    for spec in raw_specs:
        if isinstance(spec, str):
            parsed = _parse_sect_spec_string(spec)
            if parsed:
                normalized_specs.append(parsed)
            continue

        values = list(spec)
        if not values:
            continue
        name = str(values[0]).strip() or "CyberHuaTuo Sect"
        members = values[1] if len(values) == 2 and isinstance(values[1], (list, tuple, str)) else values[1:]
        normalized_specs.append((name, _normalize_sect_members(members)))

    return normalized_specs or [("CyberHuaTuo Sect", ["your-github-username"])]


def _build_sect_duel_snapshot(
    sect_name: str,
    members: list[str] | tuple[str, ...] | str,
    framework: str,
    framework_label: str,
) -> dict:
    normalized_members = _normalize_sect_members(members)
    snapshots = []
    for member in normalized_members:
        profile = get_cultivation_profile(member)
        snapshots.append(_format_duel_user_snapshot(member, profile, framework, framework_label))

    power = sum(snapshot["prescriptions"] for snapshot in snapshots)
    priority = min(
        snapshots,
        key=lambda snapshot: (snapshot["prescriptions"], normalized_members.index(snapshot["username"])),
    )
    member_args = " ".join(snapshot["username"] for snapshot in snapshots)
    command_name = _format_sect_command_name(sect_name)
    return {
        "name": sect_name.strip() or "CyberHuaTuo Sect",
        "command_name": command_name,
        "members": snapshots,
        "member_args": member_args,
        "power": power,
        "power_text": _format_duel_delta(power),
        "priority": priority,
        "sect_card_command": f"cyberhuatuo sect {command_name} {member_args} --framework {framework}",
        "sect_quest_command": f"cyberhuatuo sect-quest {command_name} {member_args} --framework {framework}",
    }


def _format_sect_duel_member_block(sect: dict, framework: str) -> list[str]:
    lines = [
        f"## {sect['name']} Members",
        f"- Sect Power: {sect['power_text']}",
        f"- Priority Member: @{sect['priority']['username']}",
        "",
    ]
    for snapshot in sect["members"]:
        username = snapshot["username"]
        lines.extend([
            f"### @{username}",
            f"- Title: {snapshot['title']}",
            f"- Prescriptions: {snapshot['prescription_text']}",
            f"- Global Rank: {snapshot['rank']}",
            f"- Current Soul Ring: {snapshot['ring']}",
            f"- Next Ring: {snapshot['next_ring']}",
            "```bash",
            f"cyberhuatuo challenge --username {username} --framework {framework}",
            f"cyberhuatuo quest {username} --framework {framework}",
            f"cyberhuatuo campaign {username} --framework {framework}",
            "```",
            "",
        ])
    return lines


def format_soul_ring_sect_duel_card(
    challenger_sect: str,
    challenger_members: list[str] | tuple[str, ...] | str,
    rival_sect: str,
    rival_members: list[str] | tuple[str, ...] | str,
    framework: str = "langchain",
) -> str:
    """Generate a real-data duel card for two Soul Ring sects/teams."""
    duel_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(duel_framework)
    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"
    challenger = _build_sect_duel_snapshot(
        challenger_sect,
        challenger_members,
        duel_framework,
        framework_label,
    )
    rival = _build_sect_duel_snapshot(
        rival_sect,
        rival_members,
        duel_framework,
        framework_label,
    )

    if challenger["power"] > rival["power"]:
        lead_line = (
            f"Current Lead: {challenger['name']} by "
            f"{_format_duel_delta(challenger['power'] - rival['power'])}"
        )
    elif rival["power"] > challenger["power"]:
        lead_line = (
            f"Current Lead: {rival['name']} by "
            f"{_format_duel_delta(rival['power'] - challenger['power'])}"
        )
    elif challenger["power"] == 0:
        lead_line = "Open Sect Duel: first real prescription lights a sect banner"
    else:
        lead_line = f"Tie Sect Duel: both sects have {_format_prescription_count(challenger['power'])}"

    command_lines = [
        challenger["sect_card_command"],
        challenger["sect_quest_command"],
        rival["sect_card_command"],
        rival["sect_quest_command"],
    ]
    for sect in (challenger, rival):
        for snapshot in sect["members"]:
            username = snapshot["username"]
            command_lines.extend([
                f"cyberhuatuo challenge --username {username} --framework {duel_framework}",
                f"cyberhuatuo quest {username} --framework {duel_framework}",
                f"cyberhuatuo campaign {username} --framework {duel_framework}",
            ])

    discussion_rows = []
    for sect in (challenger, rival):
        members = ", ".join(f"@{snapshot['username']}" for snapshot in sect["members"])
        discussion_rows.append(
            f"| {sect['name']} | {sect['power_text']} | {members} | `{sect['sect_quest_command']}` |"
        )

    return "\n".join([
        "# Soul Ring Sect Duel Card",
        "",
        f"- Challenger Sect: {challenger['name']}",
        f"- Rival Sect: {rival['name']}",
        f"- Target Framework: {framework_label} (`{duel_framework}`)",
        "- Sect Duel Formula: sum of current real prescription counts from listed GitHub members.",
        f"- {challenger['name']} Power: {challenger['power_text']}",
        f"- {rival['name']} Power: {rival['power_text']}",
        f"- {lead_line}",
        "",
        *_format_sect_duel_member_block(challenger, duel_framework),
        *_format_sect_duel_member_block(rival, duel_framework),
        "## X / Weibo",
        "```text",
        (
            f"{challenger['name']} challenges {rival['name']} to a CyberHuaTuo "
            f"Soul Ring Sect Duel in {framework_label}. {lead_line}."
        ),
        f"{challenger['name']}: {challenger['power_text']}",
        f"{rival['name']}: {rival['power_text']}",
        f"Join: {repo_url}",
        "#CyberHuaTuo #SoulRingSectDuel #AIAgents",
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        f"### Soul Ring Sect Duel: {challenger['name']} vs {rival['name']}",
        "",
        f"**Target framework:** {framework_label} (`{duel_framework}`)",
        "**Sect Duel Formula:** sum of current real prescription counts from listed GitHub members.",
        f"**Status:** {lead_line}",
        "",
        "| Sect | Real prescriptions | Members | Next action |",
        "|---|---:|---|---|",
        *discussion_rows,
        "",
        "Continue the duel:",
        "```bash",
        *command_lines,
        "```",
        "",
        f"Repo: {repo_url}",
        "````",
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "Rule: this sect duel card reports only current real prescription data; no invented wins, no invented season history.",
    ])


def format_soul_ring_sect_arena_snapshot(
    sects: list[tuple[str, list[str] | tuple[str, ...] | str]] | list[list[str]] | tuple | str,
    framework: str = "langchain",
) -> str:
    """Generate a real-data ranking snapshot for multiple Soul Ring sects/teams."""
    arena_framework = framework.strip() or "langchain"
    framework_label = _format_framework_label(arena_framework)
    repo_url = "https://github.com/JinNing6/CyberHuaTuo-Plugin"

    snapshots = []
    for index, (name, members) in enumerate(_normalize_sect_specs(sects)):
        sect = _build_sect_duel_snapshot(name, members, arena_framework, framework_label)
        sect["original_index"] = index
        snapshots.append(sect)

    ranked = sorted(snapshots, key=lambda sect: (-sect["power"], sect["original_index"]))
    for rank, sect in enumerate(ranked, 1):
        sect["arena_rank"] = rank

    champion = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None
    if champion["power"] == 0:
        champion_line = "Sect Arena is open: first real prescription claims the first sect banner"
        chase_line = "Next Chase: every sect needs 1 real prescription to claim the first banner"
    else:
        champion_line = f"Champion Sect: {champion['name']}"
        if runner_up is None:
            chase_line = "Next Chase: invite another real sect to enter the arena"
        else:
            gap = champion["power"] - runner_up["power"]
            if gap == 0:
                chase_line = (
                    f"Next Chase: {runner_up['name']} is tied with {champion['name']}; "
                    "one new real prescription breaks the tie"
                )
            else:
                chase_line = (
                    f"Next Chase: {runner_up['name']} needs {_format_duel_delta(gap)} "
                    f"to catch {champion['name']}"
                )

    chase_summary = chase_line.removeprefix("Next Chase: ")
    ranking_lines = []
    discussion_rows = []
    command_lines = []
    for sect in ranked:
        members_text = ", ".join(f"@{snapshot['username']}" for snapshot in sect["members"])
        ranking_lines.append(
            f"#{sect['arena_rank']} {sect['name']} - {sect['power_text']} ({members_text})"
        )
        discussion_rows.append(
            f"| #{sect['arena_rank']} | {sect['name']} | {sect['power_text']} | "
            f"{members_text} | `{sect['sect_quest_command']}` |"
        )
        command_lines.extend([sect["sect_card_command"], sect["sect_quest_command"]])

    if runner_up is not None:
        command_lines.append(
            f"cyberhuatuo sect-duel {runner_up['command_name']} {champion['command_name']} "
            f"--challenger-members {runner_up['member_args']} "
            f"--rival-members {champion['member_args']} --framework {arena_framework}"
        )

    for sect in ranked:
        for snapshot in sect["members"]:
            username = snapshot["username"]
            command_lines.extend([
                f"cyberhuatuo challenge --username {username} --framework {arena_framework}",
                f"cyberhuatuo quest {username} --framework {arena_framework}",
                f"cyberhuatuo campaign {username} --framework {arena_framework}",
            ])

    return "\n".join([
        "# Soul Ring Sect Arena Snapshot",
        "",
        f"- Target Framework: {framework_label} (`{arena_framework}`)",
        "- Sect Arena Formula: sum of current real prescription counts from listed GitHub members.",
        f"- {champion_line}",
        f"- {chase_line}",
        "",
        "## Sect Rankings",
        *ranking_lines,
        "",
        *[
            line
            for sect in ranked
            for line in _format_sect_duel_member_block(sect, arena_framework)
        ],
        "## X / Weibo",
        "```text",
        (
            f"CyberHuaTuo Soul Ring Sect Arena in {framework_label}: "
            f"#1 {champion['name']} with {champion['power_text']}. {chase_line}."
        ),
        f"Join: {repo_url}",
        "#CyberHuaTuo #SoulRingSectArena #AIAgents",
        "```",
        "",
        "## GitHub Discussion / PR Comment",
        "````markdown",
        "### Soul Ring Sect Arena Snapshot",
        "",
        f"**Target framework:** {framework_label} (`{arena_framework}`)",
        "**Sect Arena Formula:** sum of current real prescription counts from listed GitHub members.",
        f"**Status:** {champion_line}",
        f"**Next chase:** {chase_summary}",
        "",
        "| Rank | Sect | Real prescriptions | Members | Next action |",
        "|---:|---|---:|---|---|",
        *discussion_rows,
        "",
        "Continue the arena:",
        "```bash",
        *command_lines,
        "```",
        "",
        f"Repo: {repo_url}",
        "````",
        "",
        "## Commands",
        "```bash",
        *command_lines,
        "```",
        "",
        "Rule: this sect arena snapshot reports only current real prescription data; no invented wins, no invented season history.",
    ])


def generate_share_card(github_username: str) -> str:
    """
    生成用户的修为档案分享卡片

    可以直接粘贴到 GitHub Profile / Twitter / 微博
    """
    profile = get_cultivation_profile(github_username)
    streak_data = _load_streak(github_username)
    streak = streak_data.get("current_streak", 0)
    alchemy = get_alchemy_profile(github_username)

    # 修为进度条
    tier_index = _get_current_tier_index(profile["percentile"], profile["is_rank_one"])
    total_tiers = len(TITLE_TIERS) + 1  # +1 for 实习药童
    progress_pct = round(tier_index / total_tiers * 100)
    bar_filled = round(progress_pct / 100 * 12)
    bar_empty = 12 - bar_filled
    progress_bar = "█" * bar_filled + "░" * bar_empty

    # 心电图装饰
    ecg = "▓█▓░░▓███▓░░▓█▓░░▓█████▓░░▓█▓"

    card = (
        f"╔══════════════════════════════════════════════╗\n"
        f"║  🩺 赛博华佗 · 修为档案                      ║\n"
        f"║  CYBERHUATUO · CULTIVATION ARCHIVE           ║\n"
        f"║                                              ║\n"
        f"║  👨‍⚕️ @{github_username}\n"
        f"║  {profile['title_emoji']} 称号: {profile['title_cn']} · {profile['title_en']}\n"
    )

    # 丹术方向 + 魂环
    if alchemy["primary"]:
        p = alchemy["primary"]
        card += f"║  {p['emoji']} 主修: {p['name_cn']}丹师 · {p['rings']}\n"
        if p.get("frameworks"):
            card += f"║  🧭 战绩方向: {'/'.join(p['frameworks'][:3])}\n"
        card += f"║  🔮 {p['next_ring']['hint_cn']}\n"

    if streak > 0:
        fire = "🔥" * min(streak // 3 + 1, 5)
        card += f"║  {fire} 连续值班: {streak} 天\n"

    card += (
        f"║  💊 贡献印痕: {profile['contribution_count']} 段\n"
        f"║  🧪 修为进度: {progress_bar} {progress_pct}%\n"
    )

    # 各方向魂环展示
    if len(alchemy["directions"]) > 1:
        card += "║                                              ║\n"
        card += "║  ── 丹术方向 · ALCHEMY ──                    ║\n"
        for d in alchemy["directions"][:4]:  # 最多展示4个方向
            card += f"║  {d['emoji']} {d['name_cn']} ×{d['count']} {d['rings']}\n"

    card += (
        f"║                                              ║\n"
        f"║  ── 赛博生命体征 ──                           ║\n"
        f"║  {ecg}\n"
        f"║                                              ║\n"
        f"║  🌍 全球排名: #{profile['global_rank']} / {profile['global_total']}\n"
        f"║  ⭐ CyberHuaTuo Plugin                       ║\n"
        f"╚══════════════════════════════════════════════╝"
    )

    return card + _format_soul_ring_challenge_post(github_username, alchemy)


def _get_current_tier_index(percentile: float, is_rank_one: bool) -> int:
    """获取当前所在的称号级别索引（0=实习药童, 15=华佗再世）"""
    if is_rank_one:
        return len(TITLE_TIERS)

    for i, (threshold, _e, _cn, _en) in enumerate(reversed(TITLE_TIERS)):
        if percentile >= threshold:
            return i + 1  # +1 因为 0 是实习药童

    return 0
