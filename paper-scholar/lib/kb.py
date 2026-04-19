"""知识库 CRUD 操作。

负责 kb.json 的初始化、读写、备份，
以及论文、领域、批次的增删改查。

写入分工（与 .md 规范一致）：
- fetch 创建：papers, domains, batches(batch_id, domain, papers), meta
- reflection 补全：batches(summary_file, next_domain), meta.learning_context
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from .config import KB_JSON, KB_BACKUPS, PAPERS_DIR, LEARNING_DIR, KB_ROOT
from .exceptions import KBNotFoundError, PaperExistsError, BatchNotFoundError


# ── 读写与备份 ──────────────────────────────────────────

def init_kb() -> dict:
    """首次运行：创建目录结构和空 kb.json。

    Returns:
        初始化后的 kb 字典
    """
    KB_ROOT.mkdir(parents=True, exist_ok=True)
    PAPERS_DIR.mkdir(exist_ok=True)
    LEARNING_DIR.mkdir(exist_ok=True)
    KB_BACKUPS.mkdir(exist_ok=True)

    kb = {
        "domains": {},
        "papers": {},
        "batches": {},
        "meta": {
            "total_papers": 0,
            "total_domains": 0,
            "total_batches": 0,
            "learning_context": ""
        }
    }
    _write_kb(kb)
    return kb


def load_kb() -> dict:
    """读取 kb.json，损坏时自动从备份恢复。

    Returns:
        kb 字典

    Raises:
        KBNotFoundError: kb.json 不存在且无备份可恢复
    """
    if not KB_JSON.exists():
        raise KBNotFoundError("知识库不存在，需要先调用 init_kb()")

    # 尝试读取 kb.json
    try:
        content = KB_JSON.read_text(encoding="utf-8")
        kb = json.loads(content)
        # 验证必需字段
        _validate_kb_structure(kb)
        return kb
    except (json.JSONDecodeError, ValueError) as e:
        print(f"⚠️ kb.json 损坏: {e}")
        print("尝试从备份恢复...")
        # 尝试从最新备份恢复
        return _restore_from_backup()


def _backup_kb():
    """备份当前 kb.json 到 kb-backups/。"""
    if not KB_JSON.exists():
        return
    KB_BACKUPS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    shutil.copy2(KB_JSON, KB_BACKUPS / f"kb-{ts}.json")


def _write_kb(kb: dict):
    """写入 kb.json，自动备份旧版本（原子化写入）。

    使用临时文件 + os.replace() 确保写入的原子性，
    避免并发写入冲突导致的数据损坏。

    Args:
        kb: 要写入的 kb 字典
    """
    _backup_kb()

    # 1. 先写入临时文件
    temp_path = KB_JSON.with_suffix('.tmp')
    temp_path.write_text(
        json.dumps(kb, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # 2. 原子性重命名（os.replace 是原子操作）
    os.replace(temp_path, KB_JSON)


# ── 内部验证和恢复工具 ────────────────────────────────

def _validate_kb_structure(kb: dict):
    """验证 kb.json 的结构完整性。"""
    required_keys = {"domains", "papers", "batches", "meta"}
    missing_keys = required_keys - set(kb.keys())
    if missing_keys:
        raise ValueError(f"kb.json 缺少必需字段: {missing_keys}")

    # 验证 meta 字段
    meta_required = {"total_papers", "total_domains", "total_batches", "learning_context"}
    meta_missing = meta_required - set(kb["meta"].keys())
    if meta_missing:
        raise ValueError(f"kb.json.meta 缺少必需字段: {meta_missing}")


def _restore_from_backup() -> dict:
    """从备份恢复 kb.json。"""
    backups = sorted(KB_BACKUPS.glob("kb-*.json"))
    if not backups:
        raise RuntimeError("kb.json 损坏且无备份可恢复")

    latest_backup = backups[-1]
    print(f"从备份恢复: {latest_backup.name}")

    # 复制备份到主文件
    shutil.copy(latest_backup, KB_JSON)

    # 读取备份
    content = KB_JSON.read_text(encoding="utf-8")
    kb = json.loads(content)
    _validate_kb_structure(kb)

    print("✅ 从备份恢复成功")
    return kb


# ── 论文操作 ────────────────────────────────────────────

def add_paper(kb: dict, paper_id: str, title: str, domain: str) -> dict:
    """添加论文到知识库。

    自动更新 papers、domains、meta，自动备份 kb.json。

    Args:
        kb: 当前 kb 字典
        paper_id: 论文 ID，如 "arxiv:1706.03762"
        title: 论文标题
        domain: 所属领域，如 "NLP/Transformer"

    Returns:
        更新后的 kb 字典

    Raises:
        PaperExistsError: 论文 ID 已存在
    """
    if paper_id in kb["papers"]:
        raise PaperExistsError(f"论文 {paper_id} 已存在于知识库中")

    kb["papers"][paper_id] = {"title": title, "domain": domain}
    _ensure_domain(kb, domain)
    kb["domains"][domain]["papers"].append(paper_id)
    _update_meta_counts(kb)
    _write_kb(kb)
    return kb


def add_paper_safe(kb: dict, paper_id: str, title: str, domain: str) -> dict:
    """添加论文到知识库，已存在则静默跳过。

    与 add_paper() 功能相同，但不抛异常，适合批量处理时使用。

    Args:
        kb: 当前 kb 字典
        paper_id: 论文 ID
        title: 论文标题
        domain: 所属领域

    Returns:
        更新后的 kb 字典（无论是否实际添加）
    """
    if paper_id in kb["papers"]:
        return kb
    kb["papers"][paper_id] = {"title": title, "domain": domain}
    _ensure_domain(kb, domain)
    kb["domains"][domain]["papers"].append(paper_id)
    _update_meta_counts(kb)
    _write_kb(kb)
    return kb


def paper_exists(kb: dict, paper_id: str) -> bool:
    """检查论文是否已存在于知识库中。"""
    return paper_id in kb["papers"]


def check_duplicate_papers(kb: dict, candidates: list[dict]) -> tuple[list[dict], list[dict]]:
    """批量去重校验：在下载前与 kb.json 已有论文对比，防止重复下载。

    Args:
        kb: 当前 kb 字典
        candidates: 待下载论文列表，每项为 {"id": "arxiv:XXXX.XXXXX", "title": "..."}

    Returns:
        (new_papers, duplicates) 元组
        - new_papers: 不在知识库中的论文（需要下载）
        - duplicates: 已存在于知识库中的论文（应跳过下载）
    """
    new_papers = []
    duplicates = []
    existing_titles = {v["title"].lower().strip() for v in kb["papers"].values()}

    for paper in candidates:
        pid = paper.get("id", "")
        title = paper.get("title", "")
        title_lower = title.lower().strip()

        # 优先按 ID 精确匹配
        if pid and pid in kb["papers"]:
            duplicates.append(paper)
        # 其次按标题模糊匹配（防止同一论文 ID 不同但实际是同一篇）
        elif title_lower and title_lower in existing_titles:
            duplicates.append(paper)
        else:
            new_papers.append(paper)

    return new_papers, duplicates


def get_paper(kb: dict, paper_id: str) -> dict | None:
    """获取论文信息。

    Returns:
        {"title": ..., "domain": ...} 或 None
    """
    return kb["papers"].get(paper_id)


# ── 领域操作 ────────────────────────────────────────────

def _ensure_domain(kb: dict, domain: str):
    """确保领域存在于 domains 中，不存在则创建。

    自动建立父子关系：如 "NLP/Transformer" 会将 "Transformer"
    加入 "NLP" 的 subdomains 列表。
    """
    if domain in kb["domains"]:
        return

    parts = domain.split("/")
    path = "papers/" + domain + "/"
    entry = {"path": path, "papers": []}

    if len(parts) > 1:
        # 子领域：设置 parent，更新父领域的 subdomains
        parent = "/".join(parts[:-1])
        entry["parent"] = parent

        _ensure_domain(kb, parent)

        parent_entry = kb["domains"][parent]
        if "subdomains" not in parent_entry:
            parent_entry["subdomains"] = []
        if parts[-1] not in parent_entry["subdomains"]:
            parent_entry["subdomains"].append(parts[-1])
    else:
        # 顶级领域：初始化空 subdomains
        entry["subdomains"] = []

    kb["domains"][domain] = entry


def list_domains(kb: dict) -> list[str]:
    """列出所有领域路径。"""
    return list(kb["domains"].keys())


# ── 批次操作 ────────────────────────────────────────────

def create_batch(kb: dict, domain: str, paper_ids: list[str]) -> tuple[dict, str]:
    """fetch 创建批次记录。

    Args:
        kb: 当前 kb 字典
        domain: 批次所属领域
        paper_ids: 论文 ID 列表（仅新论文 ID）

    Returns:
        (更新后的 kb 字典, batch_id 字符串)
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    kb["batches"][ts] = {
        "batch_id": ts,
        "domain": domain,
        "papers": paper_ids
    }
    kb["meta"]["total_batches"] = len(kb["batches"])
    _write_kb(kb)
    return kb, ts


def complete_batch(kb: dict, batch_id: str,
                   summary_file: str, next_domain: str) -> dict:
    """reflection 补全批次信息。

    Args:
        kb: 当前 kb 字典
        batch_id: 批次 ID
        summary_file: 反思文件路径
        next_domain: 建议的下一个学习领域

    Returns:
        更新后的 kb 字典

    Raises:
        BatchNotFoundError: 批次 ID 不存在
    """
    if batch_id not in kb["batches"]:
        raise BatchNotFoundError(f"批次 {batch_id} 不存在")

    kb["batches"][batch_id]["summary_file"] = summary_file
    kb["batches"][batch_id]["next_domain"] = next_domain
    _write_kb(kb)
    return kb


def get_latest_batch(kb: dict) -> dict | None:
    """获取最新批次信息。"""
    if not kb["batches"]:
        return None
    latest_key = sorted(kb["batches"].keys())[-1]
    return kb["batches"][latest_key]


# ── meta 操作 ───────────────────────────────────────────

def update_learning_context(kb: dict, context: str) -> dict:
    """更新跨周期记忆桥梁（learning_context）。

    Args:
        kb: 当前 kb 字典
        context: 3-5 句话的累积学习上下文

    Returns:
        更新后的 kb 字典
    """
    kb["meta"]["learning_context"] = context
    _write_kb(kb)
    return kb


def get_progress(kb: dict) -> dict:
    """获取学习进度统计。

    Returns:
        {"total_papers": int, "total_domains": int,
         "total_batches": int, "learning_context": str}
    """
    return kb["meta"]


# ── 内部工具 ────────────────────────────────────────────

def _update_meta_counts(kb: dict):
    """根据实际数据更新 meta 计数。"""
    kb["meta"]["total_papers"] = len(kb["papers"])
    kb["meta"]["total_domains"] = len(kb["domains"])
    kb["meta"]["total_batches"] = len(kb["batches"])
# ── 任务状态跟踪 ─────────────────────────────────────

def set_task_status(status: str, info: dict = None) -> None:
    """设置任务状态。

    Args:
        status: 任务状态，可选值："running", "completed", "failed", "paused"
        info: 额外信息字典，如 {"batch_id": "...", "progress": "..."}
    """
    status_data = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "info": info or {}
    }
    status_file = KB_ROOT / ".task_status.json"
    status_file.write_text(json.dumps(status_data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_task_status() -> dict:
    """获取任务状态。

    Returns:
        任务状态字典，如果不存在则返回 {"status": "none"}
    """
    status_file = KB_ROOT / ".task_status.json"
    if not status_file.exists():
        return {"status": "none"}
    return json.loads(status_file.read_text(encoding="utf-8"))


def is_task_running() -> bool:
    """检查是否有任务正在运行。

    同时也会检查时间戳，避免僵尸任务（任务崩溃后没有清理状态）。
    如果任务状态为 "running" 但时间戳超过 2 小时，则认为任务已终止。

    Returns:
        True 表示有任务正在运行，False 表示没有
    """
    status = get_task_status()
    if status["status"] != "running":
        return False

    # 检查时间戳，避免僵尸任务
    timestamp = datetime.fromisoformat(status["timestamp"])
    elapsed = (datetime.now() - timestamp).total_seconds()

    # 如果超过 2 小时没有更新，认为任务已终止
    if elapsed > 7200:
        print(f"⚠️ 检测到僵尸任务（{elapsed:.0f}秒未更新），自动清理")
        set_task_status("paused", {"error": "僵尸任务：长时间未更新"})
        return False

    return True


def clear_task_status() -> None:
    """清理任务状态文件。

    任务完成后应该调用此函数清理状态，避免影响下一次任务。
    """
    status_file = KB_ROOT / ".task_status.json"
    try:
        if status_file.exists():
            status_file.unlink()
    except Exception as e:
        print(f"⚠️ 清理任务状态失败: {e}")
