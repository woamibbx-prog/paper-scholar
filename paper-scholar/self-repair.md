# 自修复模块

这是 paper-scholar skill 的自修复模块，负责在每轮任务执行完成后检查执行结果、发现潜在问题、并自动修复 skill 自身的漏洞。

<module_overview>
## 模块概述
- **功能**：检查执行结果、发现漏洞、自动修复
- **输入**：本轮任务执行结果（kb.json、反思文件、批次信息）
- **输出**：修复日志、修复建议、更新的 skill 文件
- **协作**：在反思模块完成后执行，作为每轮任务的最后一步
</module_overview>

<module_rules>
## 模块规则

**执行时机**：
- 每轮任务执行完成后，在反思文件生成之后
- 在标准化校验之后，作为最后一步
- 可以是自动执行（cron 任务）或手动触发

**检查范围**：
1. **数据完整性检查**
   - kb.json 与实际文件系统的一致性
   - 反思文件的格式正确性
   - 批次记录的完整性

2. **执行结果检查**
   - 论文下载成功率
   - PDF 文件完整性
   - 总结文件完整性

3. **漏洞检测**
   - 并发冲突检测
   - 解析失败检测
   - 文件损坏检测

4. **自动修复**
   - 修复数据不一致
   - 清理垃圾数据
   - 更新 skill 文件（代码和文档）

**修复原则**：
- 安全第一：只修复有把握的问题，不确定的问题记录日志
- 保留备份：修复前自动备份原始文件
- 透明记录：所有修复操作都记录到修复日志
- 用户通知：重要修复通知用户，可能需要确认
</module_rules>

<implementation>
## 实现方案

### 1. 调用时机

在 learning-reflection 模块执行完成后，调用自修复模块：

```python
# learning-reflection.md 执行流程的最后一步
# 在更新 learning_context 之后
lib.kb.update_learning_context(kb, context)

# 🔴 调用自修复模块
lib.self_repair.run_self_repair(kb, batch_id, reflection_file)

# 清理任务状态
lib.kb.clear_task_status()
```

### 2. 检查项列表

#### 2.1 数据完整性检查

**kb.json 与文件系统一致性检查**：
```python
def check_kb_filesystem_consistency(kb: dict) -> list[dict]:
    """检查 kb.json 与实际文件系统的一致性。"""
    issues = []

    # 检查所有论文的 PDF 和 summary.md 是否存在
    for paper_id, paper_info in kb["papers"].items():
        domain = paper_info["domain"]
        title = paper_info["title"]

        pdf_path = lib.config.get_pdf_path(domain, title)
        summary_path = lib.config.get_summary_path(domain, title)

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
```

#### 2.2 反思文件格式检查

**检查反思文件的格式是否符合标准化要求**：
```python
def check_reflection_format(reflection_file: str) -> list[dict]:
    """检查反思文件的格式是否符合标准化要求。"""
    issues = []
    path = lib.config.KB_ROOT / reflection_file

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
```

#### 2.3 执行结果检查

**检查本轮任务的执行结果**：
```python
def check_execution_results(kb: dict, batch_id: str) -> list[dict]:
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

        pdf_path = lib.config.get_pdf_path(domain, title)
        summary_path = lib.config.get_summary_path(domain, title)

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
```

#### 2.4 漏洞检测

**检测已知的漏洞模式**：
```python
def detect_vulnerabilities(kb: dict) -> list[dict]:
    """检测已知的漏洞模式。"""
    issues = []

    # 检查僵尸任务
    task_status = lib.kb.get_task_status()
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
    backup_dir = lib.config.KB_BACKUPS
    backups = list(backup_dir.glob("kb-*.json"))
    if len(backups) > 100:
        issues.append({
            "type": "vulnerability_detected",
            "severity": "medium",
            "message": f"kb.json 备份数量过多: {len(backups)}",
            "recommendation": "清理旧备份，检查是否有并发写入冲突"
        })

    # 检查学习进度目录中的临时文件
    temp_files = list(lib.config.LEARNING_DIR.glob("*.tmp"))
    if temp_files:
        issues.append({
            "type": "garbage_data",
            "severity": "low",
            "message": f"发现临时文件: {len(temp_files)} 个",
            "files": [str(f) for f in temp_files]
        })

    return issues
```

### 3. 自动修复方案

#### 3.1 清理垃圾数据

```python
def clean_garbage_data(kb: dict) -> dict:
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
        pdf_path = lib.config.get_pdf_path(domain, title)

        if pdf_path.exists() and pdf_path.stat().st_size == 0:
            pdf_path.unlink()
            cleanup_report["deleted_pdfs"].append(paper_id)
            print(f"🗑️ 删除 0 字节 PDF: {paper_id}")

    # 清理临时文件
    for temp_file in lib.config.LEARNING_DIR.glob("*.tmp"):
        temp_file.unlink()
        cleanup_report["deleted_temp_files"].append(str(temp_file))
        print(f"🗑️ 删除临时文件: {temp_file.name}")

    # 清理空目录
    for empty_dir in lib.config.PAPERS_DIR.rglob("*"):
        if empty_dir.is_dir() and not any(empty_dir.iterdir()):
            empty_dir.rmdir()
            cleanup_report["deleted_empty_dirs"].append(str(empty_dir))
            print(f"🗑️ 删除空目录: {empty_dir}")

    return cleanup_report
```

#### 3.2 修复数据不一致

```python
def repair_kb_inconsistency(kb: dict) -> dict:
    """修复 kb.json 与文件系统的不一致。"""
    repair_report = {
        "fixed_missing_papers": [],
        "fixed_invalid_batches": []
    }

    # 移除 kb.json 中记录但文件不存在的论文
    papers_to_remove = []
    for paper_id, paper_info in kb["papers"].items():
        domain = paper_info["domain"]
        title = paper_info["title"]
        pdf_path = lib.config.get_pdf_path(domain, title)

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
    for domain_name, domain_info in kb["domains"].items():
        if not domain_info["papers"]:
            domains_to_remove.append(domain_name)
            repair_report["fixed_invalid_batches"].append(domain_name)

    for domain_name in domains_to_remove:
        del kb["domains"][domain_name]
        print(f"🔧 从 kb.json 移除空的域: {domain_name}")

    # 更新 kb.json
    if papers_to_remove or domains_to_remove:
        kb = lib.kb._update_meta_counts(kb)
        lib.kb._write_kb(kb)

    return repair_report
```

#### 3.3 更新 skill 文件

```python
def update_skill_files_if_needed(issues: list[dict]) -> dict:
    """根据发现的问题，更新 skill 文件（代码和文档）。"""
    update_report = {
        "updated_files": [],
        "patches_applied": []
    }

    # 这里是占位符，实际实现需要根据具体问题进行修复
    # 例如：
    # - 如果发现 parse_part4() 的解析失败率高，可以优化解析逻辑
    # - 如果发现某个模块频繁出错，可以增强错误处理
    # - 如果发现文档描述不清楚，可以更新文档

    # 示例：更新 CHANGELOG
    if any(issue["type"] == "vulnerability_detected" for issue in issues):
        print("📝 检测到漏洞，考虑更新 skill 文件...")
        # 这里可以添加自动修复代码
        # 例如更新 lib/kb.py 中的并发写入逻辑

    return update_report
```

### 4. 主函数

```python
def run_self_repair(kb: dict, batch_id: str, reflection_file: str) -> dict:
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
    report_path = lib.config.KB_ROOT / f"repair_report_{batch_id}.json"
    report_path.write_text(json.dumps(repair_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"📄 修复报告已保存: {report_path.name}")

    return repair_report
```

## 在 learning-reflection 模块中调用

在 learning-reflection.md 的最后，添加自修复调用：

```markdown
**输出阶段**：
1. 调用 `lib.reflection_utils.write_reflection(content)` 写入反思文件
2. 调用 `lib.kb.complete_batch(kb, batch_id, summary_file, next_domain)` 补全批次信息
3. 调用 `lib.kb.update_learning_context(kb, context)` 更新 learning_context
4. **🔴 新增**：调用 `lib.self_repair.run_self_repair(kb, batch_id, summary_file)` 执行自修复
5. 调用 `lib.kb.clear_task_status()` 清理任务状态
```
</implementation>

<workflow>
## 工作流程

```
任务完成
    ↓
生成反思文件
    ↓
更新 kb.json
    ↓
🔍 调用自修复模块
    ↓
    ├─→ 检查数据完整性
    ├─→ 检查反思文件格式
    ├─→ 检查执行结果
    └─→ 检测漏洞
    ↓
🔧 自动修复
    ↓
    ├─→ 清理垃圾数据
    ├─→ 修复数据不一致
    └─→ 更新 skill 文件（如果有必要）
    ↓
📊 生成修复报告
    ↓
周期完成
```
</workflow>

<example>
## 示例输出

```python
🔍 开始自修复检查...
📋 检查数据完整性...
📋 检查反思文件格式...
📋 检查执行结果...
📋 检测漏洞...
🔧 开始自动修复...
  🗑️ 清理垃圾数据...
🗑️ 删除 0 字节 PDF: arxiv:2103.12345
🗑️ 删除临时文件: temp_summary_20260417.tmp
🔧 修复数据不一致...
🔧 从 kb.json 移除缺失的论文: arxiv:2103.12345

📊 自修复完成:
  总问题数: 3
  🔴 高严重性: 1
  🟡 中等严重性: 1
  🟢 低严重性: 1

📄 修复报告已保存: repair_report_2026-04-17_14-30-00.json
```
</example>

## Keywords

self-repair, automated-fix, bug-detection, data-consistency, automated-maintenance, self-healing
