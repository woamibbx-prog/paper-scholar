"""自修复模块。

在每轮任务执行完成后，检查执行结果、发现潜在问题、并自动修复 skill 自身的漏洞。
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from .config import KB_ROOT, KB_JSON, KB_BACKUPS, PAPERS_DIR, LEARNING_DIR
from . import kb as kb_lib
from . import reflection_utils as ref_utils
from .config import get_pdf_path, get_summary_path


# ── 检查函数 ────────────────────────────────────────────

def check_kb_filesystem_consistency(kb: dict) -> List[Dict]:
    """检查 kb.json 与实际文件系统的一致性。"""
    issues = []

    # 检查所有论文的 PDF 和 summary.md 是否存在
    for paper_id, paper_info in kb["papers"].items():
        domain = paper_info["domain"]
        title = paper_info["title"]

        pdf_path = get_pdf_path(domain, title)
        summary_path = get_summary_path(domain, title)

        if not pdf_path.exists():
            issues.append({
                "type": "missing_file",
                "severity": "medium",
                "message": f"论文 PDF 缺失: {paper_id}",
                "paper_id": paper_id,
                "missing_file": str(pdf_path)
            })

        if not summary_path.exists():
            issues.append({
                "type": "missing_file",
                "severity": "low",
                "message": f"总结文件缺失: {paper_id}",
                "paper_id": paper_id,
                "missing_file": str(summary_path)
            })

    # 检查批次记录的完整性
    for batch_id, batch_info in kb["batches"].items():
        if "summary_file" not in batch_info or not batch_info["summary_file"]:
            issues.append({
                "type": "incomplete_batch",
                "severity": "medium",
                "message": f"批次记录不完整: {batch_id}（缺少 summary_file）",
                "batch_id": batch_id
            })

    return issues


def check_reflection_format(reflection_file: str) -> List[Dict]:
    """检查反思文件的格式是否符合标准化要求。"""
    issues = []
    path = KB_ROOT / reflection_file

    if not path.exists():
        issues.append({
            "type": "missing_file",
            "severity": "high",
            "message": f"反思文件不存在: {reflection_file}"
        })
        return issues

    content = path.read_text(encoding="utf-8")

    # 检查文件名格式
    filename = path.name
    if not re.match(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}(_\d+)?\.md", filename):
        issues.append({
            "type": "format_error",
            "severity": "medium",
            "message": f"反思文件名格式错误: {filename}（应为 YYYY-MM-DD_HH-MM-SS.md）",
            "file": filename
        })

    # 检查 PART 结构
    for i in range(1, 5):
        if f"## PART {i}" not in content and f"##PART {i}" not in content:
            issues.append({
                "type": "format_error",
                "severity": "medium",
                "message": f"反思文件缺少 PART {i}",
                "file": filename
            })

    # 检查 PART 4 标签格式
    part4_match = re.search(r"##\s*PART\s*4[:\s]*.*?\n(.+?)(?=\n##\s*PART|\Z)", content, re.DOTALL)
    if part4_match:
        part4_text = part4_match.group(1)
        if not re.search(r"【继续当前领域】|【转向相关领域】", part4_text):
            issues.append({
                "type": "format_error",
                "severity": "high",
                "message": "PART 4 缺少正确的【标签】格式",
                "file": filename
            })

    return issues


def check_execution_results(kb: dict, batch_id: str) -> List[Dict]:
    """检查本轮任务的执行结果。"""
    issues = []

    batch_info = kb["batches"].get(batch_id)
    if not batch_info:
        issues.append({
            "type": "data_error",
            "severity": "high",
            "message": f"批次记录不存在: {batch_id}"
        })
        return issues

    # 检查论文数量
    paper_count = len(batch_info["papers"])
    if paper_count == 0:
        issues.append({
            "type": "execution_warning",
            "severity": "low",
            "message": f"本轮未下载任何论文（可能所有候选论文都已存在）",
            "batch_id": batch_id
        })

    # 检查每个论文的文件完整性
    for paper_id in batch_info["papers"]:
        paper_info = kb["papers"][paper_id]
        domain = paper_info["domain"]
        title = paper_info["title"]

        pdf_path = get_pdf_path(domain, title)
        summary_path = get_summary_path(domain, title)

        # 检查 PDF 文件大小
        if pdf_path.exists():
            pdf_size = pdf_path.stat().st_size
            if pdf_size == 0:
                issues.append({
                    "type": "invalid_file",
                    "severity": "high",
                    "message": f"PDF 文件大小为 0: {paper_id}",
                    "paper_id": paper_id,
                    "file": str(pdf_path)
                })

    return issues


def detect_vulnerabilities(kb: dict) -> List[Dict]:
    """检测已知的漏洞模式。"""
    issues = []

    # 检查僵尸任务
    task_status = kb_lib.get_task_status()
    if task_status.get("status") == "running":
        timestamp = datetime.fromisoformat(task_status["timestamp"])
        elapsed = (datetime.now() - timestamp).total_seconds()
        if elapsed > 7200:  # 超过 2 小时
            issues.append({
                "type": "vulnerability_detected",
                "severity": "medium",
                "message": f"检测到僵尸任务（{elapsed:.0f}秒未更新）",
                "recommendation": "清理任务状态文件"
            })

    # 检查 kb.json 备份数量（如果太多，可能说明有频繁的并发写入）
    backups = list(KB_BACKUPS.glob("kb-*.json"))
    if len(backups) > 100:
        issues.append({
            "type": "vulnerability_detected",
            "severity": "medium",
            "message": f"kb.json 备份数量过多: {len(backups)}",
            "recommendation": "清理旧备份，检查是否有并发写入冲突"
        })

    # 检查学习进度目录中的临时文件
    temp_files = list(LEARNING_DIR.glob("*.tmp"))
    if temp_files:
        issues.append({
            "type": "garbage_data",
            "severity": "low",
            "message": f"发现临时文件: {len(temp_files)} 个",
            "files": [str(f) for f in temp_files]
        })

    return issues


# ── 修复函数 ────────────────────────────────────────────

def clean_garbage_data(kb: dict) -> Dict:
    """清理垃圾数据（0字节PDF、临时文件、空目录）。"""
    cleanup_report = {
        "deleted_pdfs": [],
        "deleted_temp_files": [],
        "deleted_empty_dirs": []
    }

    # 清理 0 字节 PDF
    for paper_id, paper_info in kb["papers"].items():
        domain = paper_info["domain"]
        title = paper_info["title"]
        pdf_path = get_pdf_path(domain, title)

        if pdf_path.exists() and pdf_path.stat().st_size == 0:
            pdf_path.unlink()
            cleanup_report["deleted_pdfs"].append(paper_id)
            print(f"🗑️ 删除 0 字节 PDF: {paper_id}")

    # 清理临时文件
    for temp_file in LEARNING_DIR.glob("*.tmp"):
        temp_file.unlink()
        cleanup_report["deleted_temp_files"].append(str(temp_file))
        print(f"🗑️ 删除临时文件: {temp_file.name}")

    # 清理空目录
    for empty_dir in PAPERS_DIR.rglob("*"):
        if empty_dir.is_dir() and not any(empty_dir.iterdir()):
            try:
                empty_dir.rmdir()
                cleanup_report["deleted_empty_dirs"].append(str(empty_dir))
                print(f"🗑️ 删除空目录: {empty_dir}")
            except OSError:
                # 目录可能不为空或无法删除，跳过
                pass

    return cleanup_report


def repair_kb_inconsistency(kb: dict) -> Dict:
    """修复 kb.json 与文件系统的不一致。"""
    repair_report = {
        "fixed_missing_papers": [],
        "fixed_empty_domains": []
    }

    # 移除 kb.json 中记录但文件不存在的论文
    papers_to_remove = []
    for paper_id, paper_info in kb["papers"].items():
        domain = paper_info["domain"]
        title = paper_info["title"]
        pdf_path = get_pdf_path(domain, title)

        if not pdf_path.exists():
            papers_to_remove.append(paper_id)
            repair_report["fixed_missing_papers"].append(paper_id)
            print(f"🔧 从 kb.json 移除缺失的论文: {paper_id}")

    # 从 domains 中移除论文引用
    for paper_id in papers_to_remove:
        if paper_id in kb["papers"]:
            domain = kb["papers"][paper_id]["domain"]
            if domain in kb["domains"] and paper_id in kb["domains"][domain]["papers"]:
                kb["domains"][domain]["papers"].remove(paper_id)
            del kb["papers"][paper_id]

    # 清理空的域
    domains_to_remove = []
    for domain_name, domain_info in list(kb["domains"].items()):
        if not domain_info["papers"]:
            domains_to_remove.append(domain_name)
            repair_report["fixed_empty_domains"].append(domain_name)
            print(f"🔧 从 kb.json 移除空的域: {domain_name}")

    for domain_name in domains_to_remove:
        del kb["domains"][domain_name]

    # 更新 kb.json
    if papers_to_remove or domains_to_remove:
        kb = kb_lib._update_meta_counts(kb)
        kb_lib._write_kb(kb)

    return repair_report


def update_skill_files_if_needed(issues: List[Dict]) -> Dict:
    """根据发现的问题，更新 skill 文件（代码和文档）。"""
    update_report = {
        "updated_files": [],
        "patches_applied": [],
        "recommendations": []
    }

    # 这里是占位符，实际实现需要根据具体问题进行修复
    # 例如：
    # - 如果发现 parse_part4() 的解析失败率高，可以优化解析逻辑
    # - 如果发现某个模块频繁出错，可以增强错误处理
    # - 如果发现文档描述不清楚，可以更新文档

    # 示例：如果检测到高严重性问题，给出建议
    high_severity_issues = [issue for issue in issues if issue.get("severity") == "high"]
    if high_severity_issues:
        update_report["recommendations"].append("检测到高严重性问题，建议检查日志并考虑更新 skill 文件")

    return update_report


# ── 主函数 ──────────────────────────────────────────────

def run_self_repair(kb: dict, batch_id: str, reflection_file: str) -> Dict:
    """执行完整的自修复流程。

    Args:
        kb: 当前知识库
        batch_id: 本轮批次 ID
        reflection_file: 本轮反思文件路径

    Returns:
        修复报告
    """
    print("🔍 开始自修复检查...")

    repair_report = {
        "timestamp": datetime.now().isoformat(),
        "batch_id": batch_id,
        "checks": {},
        "fixes": {},
        "issues": []
    }

    # 1. 数据完整性检查
    print("📋 检查数据完整性...")
    consistency_issues = check_kb_filesystem_consistency(kb)
    repair_report["checks"]["consistency"] = consistency_issues

    # 2. 反思文件格式检查
    print("📋 检查反思文件格式...")
    format_issues = check_reflection_format(reflection_file)
    repair_report["checks"]["reflection_format"] = format_issues

    # 3. 执行结果检查
    print("📋 检查执行结果...")
    execution_issues = check_execution_results(kb, batch_id)
    repair_report["checks"]["execution"] = execution_issues

    # 4. 漏洞检测
    print("📋 检测漏洞...")
    vulnerability_issues = detect_vulnerabilities(kb)
    repair_report["checks"]["vulnerabilities"] = vulnerability_issues

    # 汇总所有问题
    all_issues = consistency_issues + format_issues + execution_issues + vulnerability_issues
    repair_report["issues"] = all_issues

    # 5. 自动修复
    print("🔧 开始自动修复...")

    # 清理垃圾数据
    if any(issue["type"] in ["invalid_file", "garbage_data"] for issue in all_issues):
        print("  🗑️ 清理垃圾数据...")
        cleanup_report = clean_garbage_data(kb)
        repair_report["fixes"]["cleanup"] = cleanup_report

    # 修复数据不一致
    if any(issue["type"] == "missing_file" for issue in consistency_issues):
        print("  🔧 修复数据不一致...")
        repair_report = repair_kb_inconsistency(kb)
        repair_report["fixes"]["kb_repair"] = repair_report

    # 更新 skill 文件（如果有必要）
    high_severity_issues = [issue for issue in all_issues if issue.get("severity") == "high"]
    if high_severity_issues:
        print("  📝 检测到高严重性问题，考虑更新 skill 文件...")
        update_report = update_skill_files_if_needed(high_severity_issues)
        repair_report["fixes"]["skill_update"] = update_report

    # 6. 生成修复报告
    total_issues = len(all_issues)
    high_severity = sum(1 for issue in all_issues if issue.get("severity") == "high")
    medium_severity = sum(1 for issue in all_issues if issue.get("severity") == "medium")
    low_severity = sum(1 for issue in all_issues if issue.get("severity") == "low")

    print(f"\n📊 自修复完成:")
    print(f"  总问题数: {total_issues}")
    print(f"  🔴 高严重性: {high_severity}")
    print(f"  🟡 中等严重性: {medium_severity}")
    print(f"  🟢 低严重性: {low_severity}")

    # 保存修复报告
    report_path = KB_ROOT / f"repair_report_{batch_id}.json"
    report_path.write_text(json.dumps(repair_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"📄 修复报告已保存: {report_path.name}")

    return repair_report
