"""反思文件读写与 PART 4 解析。

负责反思文件的写入、读取，以及从反思文本中
提取"下一步学习计划"的结构化信息。
"""

import os
import re
from datetime import datetime

from .config import LEARNING_DIR, get_latest_reflection
from .exceptions import ReflectionParseError


# ── 反思文件写入 ───────────────────────────────────────

def write_reflection(content: str) -> str:
    """写入反思文件，确保时间戳唯一和写入安全。

    自动用当前时间生成文件名（YYYY-MM-DD_HH-MM-SS.md），
    存储到 learning-progress/ 目录。

    如果时间戳冲突，自动添加后缀确保唯一性。

    Args:
        content: 反思文件的完整 Markdown 内容

    Returns:
        kb.json 中 summary_file 字段所需的相对路径，
        如 "learning-progress/2026-04-12_14-30-00.md"
    """
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)

    # 确保时间戳唯一（如果有冲突，添加微秒）
    for i in range(10):
        if i == 0:
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        else:
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + f"_{i}"
        filename = f"{ts}.md"
        path = LEARNING_DIR / filename

        # 检查文件是否已存在
        if not path.exists():
            break

    # 写入文件
    path.write_text(content, encoding="utf-8")
    return f"learning-progress/{filename}"


# ── 反思文件读取 ───────────────────────────────────────

def read_latest_reflection() -> str | None:
    """读取最新反思文件的内容。

    Returns:
        反思文件内容（Markdown 字符串），无反思时返回 None
    """
    path = get_latest_reflection()
    if path and path.exists():
        return path.read_text(encoding="utf-8")
    return None


def read_reflection(filename: str) -> str | None:
    """读取指定反思文件。

    Args:
        filename: 文件名，如 "2026-04-12_14-30-00.md"

    Returns:
        反思内容，文件不存在时返回 None
    """
    path = LEARNING_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


# ── PART 4 解析 ────────────────────────────────────────

def parse_part4(reflection_content: str) -> dict:
    """从反思文本中解析 PART 4（下一步学习计划）。

    提取结构化信息：
    - action: "continue"（继续当前领域）或 "new_domain"（转向新领域）
    - direction / domain / learning_path: 具体方向信息
    - raw: PART 4 原始文本
    - safe_mode: 是否为安全模式（解析失败时为 True）
    - error: 错误信息（安全模式下）

    Args:
        reflection_content: 反思文件的完整 Markdown 内容

    Returns:
        解析结果字典。如果解析失败，返回 safe_mode 的默认结果。
    """
    try:
        # 提取 PART 4 内容
        match = re.search(
            r"##\s*PART\s*4[:\s]*.*?\n(.+?)(?=\n##\s*PART|\Z)",
            reflection_content,
            re.DOTALL | re.IGNORECASE
        )
        if not match:
            # 降级策略：返回安全模式
            return {
                "action": "continue",
                "direction": "继续学习当前领域",
                "keywords": [],
                "raw": "",
                "safe_mode": True,
                "error": "PART 4 解析失败，使用安全模式"
            }

        text = match.group(1).strip()
        result = {"raw": text, "action": "unknown", "safe_mode": False}

        # 判断动作类型
        if _is_continue(text):
            result["action"] = "continue"
            result["direction"] = _extract_direction(text)
            result["keywords"] = _extract_keywords(text)
        elif _is_new_domain(text):
            result["action"] = "new_domain"
            result["domain"] = _extract_new_domain(text)
            result["learning_path"] = _extract_learning_path(text)
            result["keywords"] = _extract_keywords(text)
        else:
            # 无法判断动作类型，返回安全模式
            result["safe_mode"] = True
            result["action"] = "continue"
            result["error"] = "无法判断动作类型，使用安全模式继续当前领域"

        return result

    except Exception as e:
        # 意外错误，返回安全模式
        return {
            "action": "continue",
            "direction": "继续学习当前领域",
            "keywords": [],
            "raw": "",
            "safe_mode": True,
            "error": f"解析失败: {str(e)}"
        }


# ── 内部解析工具 ───────────────────────────────────────

# 【】中不属于搜索关键词的标签词
_TAG_BLACKLIST = {
    "继续当前领域", "转向相关领域", "或转向相关领域",
    "继续学习", "下一步", "计划",
}


def _is_continue(text: str) -> bool:
    """判断是否为"继续当前领域"。

    优先匹配【标签】，再匹配关键词。
    """
    # 优先级1：精确匹配【标签】
    if re.search(r"【继续当前领域】", text):
        return True
    # 优先级2：关键词匹配（仅在没有【转向】标签时生效）
    if re.search(r"【.*?转向", text):
        return False
    # 优先级3：宽松匹配
    return bool(re.search(r"继续.*?领域", text))


def _is_new_domain(text: str) -> bool:
    """判断是否为"转向新领域"。"""
    # 优先级1：精确匹配【标签】
    if re.search(r"【.*?转向", text):
        return True
    # 优先级2：关键词匹配
    patterns = [
        r"转向.*?(相关|新)?领域",
        r"新领域[：:]",
        r"新开领域",
        r"转向相关领域",
    ]
    return any(re.search(p, text) for p in patterns)


def _extract_direction(text: str) -> str:
    """提取"继续当前领域"的具体方向。"""
    patterns = [
        r"具体方向[：:]\s*(.+)",
        r"方向[：:]\s*(.+)",
        r"学习目标[：:]\s*(.+)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip()
    return ""


def _extract_new_domain(text: str) -> str:
    """提取新领域名称。"""
    patterns = [
        r"新领域[：:]\s*(.+?)(?:\n|$)",
        r"新开领域[：:]\s*(.+?)(?:\n|$)",
        r"转向.*?领域[：:]\s*(.+?)(?:\n|$)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip()
    return ""


def _extract_learning_path(text: str) -> str:
    """提取学习路径。"""
    m = re.search(r"学习路径[：:]\s*(.+)", text)
    return m.group(1).strip() if m else ""


def _split_search_terms(text: str) -> list[str]:
    """将一段文本拆分为搜索词。

    支持的分隔符：中英文逗号、顿号、分号、箭头。
    过滤掉"如"字开头的示例前缀。
    """
    text = re.sub(r"^如\s*", "", text.strip())
    parts = re.split(r"[,，、；;→➡]+", text)
    return [p.strip() for p in parts if p.strip()]


def _extract_keywords(text: str) -> list[str]:
    """从 PART 4 中提取搜索关键词。

    提取方向、领域、技术名词等作为搜索词。
    过滤掉【】中的标签词（如"继续当前领域"）。
    """
    keywords: list[str] = []

    # 提取【】中的内容，但过滤掉标签词
    bracket_items = re.findall(r"【(.+?)】", text)
    for item in bracket_items:
        if item not in _TAG_BLACKLIST:
            keywords.append(item)

    # 提取"具体方向"/"学习目标"后的内容，拆分为细粒度关键词
    direction = _extract_direction(text)
    if direction:
        keywords.extend(_split_search_terms(direction))

    new_domain = _extract_new_domain(text)
    if new_domain:
        keywords.extend(_split_search_terms(new_domain))

    # 去重并保持顺序
    seen: set[str] = set()
    unique: list[str] = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique.append(k)

    return unique
