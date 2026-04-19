"""路径常量与配置。

所有 paper-scholar 的路径规则集中在此文件，
避免各处手拼路径导致不一致。
"""

from pathlib import Path

# 知识库根路径
KB_ROOT = Path.home() / ".paper-scholar"
KB_JSON = KB_ROOT / "kb" / "kb.json"
KB_BACKUPS = KB_ROOT / "kb" / "kb-backups"
PAPERS_DIR = KB_ROOT / "papers"
LEARNING_DIR = KB_ROOT / "learning-progress"


def get_paper_dir(domain: str, paper_title: str) -> Path:
    """获取论文存储目录（绝对路径）。

    Args:
        domain: 领域路径，如 "ULM/[领域]深度学习定位与检测"
        paper_title: 论文标题，如 "Attention Is All You Need"

    Returns:
        绝对路径，如 ~/.paper-scholar/papers/ULM/[领域]深度学习定位与检测/[论文] Attention_Is_All_You_Need/
    """
    safe_title = paper_title.replace(" ", "_")
    return PAPERS_DIR / domain / safe_title


def get_relative_paper_dir(domain: str, paper_title: str) -> str:
    """获取论文存储目录（相对路径字符串，用于批次清单传递）。

    统一使用正斜杠，跨平台一致。

    Returns:
        "papers/ULM/[领域]深度学习定位与检测/[论文] Attention_Is_All_You_Need/"
    """
    path = get_paper_dir(domain, paper_title)
    rel = str(path.relative_to(KB_ROOT)).replace("\\", "/")
    return rel + "/"


def get_summary_path(domain: str, paper_title: str) -> Path:
    """获取论文总结文件路径。"""
    return get_paper_dir(domain, paper_title) / "summary.md"


def get_pdf_path(domain: str, paper_title: str) -> Path:
    """获取论文 PDF 文件路径。"""
    return get_paper_dir(domain, paper_title) / "paper.pdf"


def get_reflection_path(timestamp: str, top_domain: str = "") -> Path:
    """根据时间戳获取反思文件路径。

    Args:
        timestamp: 格式 YYYY-MM-DD_HH-MM-SS
        top_domain: 顶级领域名（如 "ULM"），用于子目录分类
    """
    if top_domain:
        return LEARNING_DIR / top_domain / f"{timestamp}.md"
    return LEARNING_DIR / f"{timestamp}.md"


def get_latest_reflection(top_domain: str = "") -> Path | None:
    """获取 learning-progress/ 中最新的反思文件。

    Args:
        top_domain: 顶级领域名（如 "ULM"），搜索对应子目录

    Returns:
        最新的 .md 文件路径，目录不存在或为空时返回 None
    """
    search_dir = LEARNING_DIR / top_domain if top_domain else LEARNING_DIR
    if not search_dir.exists():
        return None
    files = sorted(search_dir.glob("*.md"))
    return files[-1] if files else None
