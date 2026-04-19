# 获取模块

这是 paper-scholar skill 的获取模块，负责搜索论文、批量下载 PDF 并完成储存。

<module_overview>
## 模块概述
- **功能**：搜索论文、批量下载并完成储存
- **输入**：领域描述 + 筛选条件
- **输出**：完成的目录结构 + 更新后的 kb.json + 本次论文列表
- **协作**：与知识库协作更新元数据，从反思模块读取领域建议，输出论文列表给 summarize 模块
</module_overview>

<module_rules>
## 模块规则

### 领域判断规则
- **场景1：用户指定领域**
  ```
  输入: "我要学习 NLP 领域"
  动作:
  - 直接搜索 "NLP" 相关论文
  - 领域路径确定为: kb/papers/NLP/
  - 创建目录结构 kb/papers/NLP/
  ```

- **场景2：继续学习**
  ```
  输入: "继续学习"
  动作:
  1. 调用 lib.reflection_utils.read_latest_reflection() 读取最新反思
  2. 调用 lib.reflection_utils.parse_part4(content) 解析 PART 4
  3. 根据解析结果（action + keywords）确定搜索领域和关键词
  ```

**PART 4 解析规则**：
- 调用 `lib.reflection_utils.parse_part4(content)` 自动解析
- 如果返回 action="continue" → 搜索领域 = 当前领域 + keywords
  - 当前领域通过 `lib.kb.get_latest_batch(kb)["domain"]` 获取
  - 示例：当前领域 NLP/Transformer，keywords=["FlashAttention", "优化"] → 搜索 "FlashAttention efficient transformer"
- 如果返回 action="new_domain" → 搜索领域 = 新领域路径
  - 示例：domain="GPT", keywords=["GPT", "自回归语言模型"] → 搜索 "GPT autoregressive language model"
- 如果返回 action="unknown" → 回退方案：自行阅读反思文件 PART 4 原文，理解意图后确定搜索方向
- keywords 组合为搜索词：将关键词用空格拼接，中文关键词翻译为英文搜索

**领域路径判断**：
- 新顶级领域 → kb/papers/新领域/
- 已有子领域 → kb/papers/父领域/子领域/
- 嵌套领域 → kb/papers/A/B/C/

**与反思的协作**：
- fetch 模块从反思文件中读取 "下一步学习计划"
- 根据计划决定搜索的领域和关键词
- 将领域信息通过批次清单传递给 summarize，由 summarize 透传给 learning-reflection

### 搜索规则
- 使用 arXiv API 进行搜索
- 每批次最多返回 10 篇论文

### 筛选标准
1. **高影响力**：被引量 > 100（或领域内前 50%）
2. **时效性**：近 5 年内的论文优先
3. **相关性**：标题和摘要包含领域核心关键词
4. **创新性**：方法、技术或应用上有显著突破
5. **全面性**：覆盖领域内主要研究方向

### 排序权重
- 被引量（权重 40%）
- 下载量（权重 30%）
- 发表时间（权重 20%）：近 3 年论文 +1 分，近 5 年 +0.5 分
- 领域匹配度（权重 10%）

### 排除条件
- 被引量 < 50（除非是新领域）
- 发表时间 > 10 年
- 纯理论性论文（除非该领域以理论为主）
- 重复性研究（在相同数据集上重复已有工作）
- 低质量论文（如明显错误或抄袭）

### 自定义选项
- 时间范围：可指定年份范围（如近 3 年）
- 关键词：支持多关键词组合
- 排序方式：可按被引量、下载量或发表时间排序
- 领域细化：可指定子领域（如 "NLP/Transformer" 而不是 "NLP"）

### 下载规则
- 并发下载：最多 5 个同时下载
- 超时设置：单个下载超时 30 秒
- 重试机制：失败后最多重试 3 次
- 文件大小限制：单个 PDF 不超过 100MB

### 存储规则
- 文件名：论文标题（空格替换为下划线）
- 目录名：必须加 `[论文] ` 前缀（注意空格），如 `[论文] Attention Is All You Need`
- 领域目录名：必须加 `[领域]` 前缀（无空格），如 `[领域]Chain-of-Thought_Reasoning`
- 域名处理：支持多级目录（如 NLP/Transformer/GPT）
- 路径规范化：统一使用正斜杠 `/`
- **禁止中文翻译**：标题仅使用英文，不添加中文翻译（包括括号中的中文）

**创建后立即校验（刚性要求）**：
- 每次创建新文件夹后，必须立即检查前缀是否正确
- 领域文件夹 → 必须以 `[领域]` 开头，如 `[领域]Efficient_Inference`
- 论文文件夹 → 必须以 `[论文] ` 开头（注意空格），如 `[论文] Attention Is All You Need`
- 如果发现前缀缺失或格式错误，**立即重命名修复**，不可留到自检阶段
- 禁止格式：`[论文]Title (中文翻译)`、`[论文]Title_标题`、`[领域] 名称 (English)`

### 错误处理
- 搜索失败：返回空列表，记录错误日志
- 下载失败：标记为 failed，继续下载其他论文
- 存储失败：回滚已下载的论文，保持知识库一致性
- 网络错误：自动重试，最多 3 次
</module_rules>


<kb_interaction>
## 知识库交互流程

**步骤1：读取现有知识库**
- 调用 `lib.kb.load_kb()` → 返回 kb 字典
  - 若抛 KBNotFoundError → 调用 `lib.kb.init_kb()` 初始化
- 从返回的 kb 中读取 `meta.learning_context` 快速恢复全局认知
- 如果是"继续学习"场景，调用 `lib.reflection_utils.read_latest_reflection()` 读取最新反思

**步骤1.5：下载前去重校验（刚性要求）**
- 在执行任何 PDF 下载之前，必须先调用 `lib.kb.check_duplicate_papers(kb, candidates)` 进行批量去重
- `candidates` 格式：`[{"id": "arxiv:XXXX.XXXXX", "title": "Paper Title"}, ...]`
- 函数返回 `(new_papers, duplicates)`
- **仅对 `new_papers` 执行后续下载流程**，`duplicates` 中的论文不发起任何网络请求
- 在批次输出 / 日志中明确标注被跳过的重复论文：`已跳过：arxiv:XXXX.XXXXX "Title"（已存在于知识库）`
- 如果 `new_papers` 为空（所有候选都是重复），跳过步骤 2-4，直接进入反思模块告知无新论文

**步骤2：下载并添加论文**
- 仅对步骤 1.5 返回的 `new_papers` 执行下载
- 遍历 `new_papers`，逐篇下载 PDF 并调用 `lib.kb.add_paper(kb, paper_id, title, domain)` 添加到知识库
- 由于步骤 1.5 已保证无重复，此处使用 `add_paper`（重复时会抛 `PaperExistsError`，作为安全网）
- 论文存储路径通过 `lib.config.get_paper_dir(domain, title)` 获取（绝对路径，用于文件操作）
- **重要**：如果所有论文都被跳过（无新论文），跳过步骤 3-4，直接进入反思模块告知无新论文

**下载成功后的立即校验**：
- 检查下载的PDF文件大小是否 > 0字节（0字节视为无效）
- 检查论文文件夹名称是否包含正确的前缀（`[论文] `）
- 检查领域文件夹名称是否包含正确的前缀（`[领域]`）
- 如果发现前缀缺失，立即重命名修复
- 如果发现0字节PDF，记录日志，后续重新下载

**步骤3：创建批次记录**
- 调用 `kb, batch_id = lib.kb.create_batch(kb, domain, paper_ids)`
- 返回值是 `(kb字典, batch_id字符串)` 的元组
- paper_ids = 本批次实际新增的论文 ID 列表（被跳过的不计入）
- kb.json 自动备份（每次 _write_kb 时自动备份）

**步骤4：生成批次清单**
- 用步骤 3 返回的 `batch_id` 构建批次清单
- 论文路径：调用 `lib.config.get_relative_paper_dir(domain, title)` 获取相对路径字符串
- total_count = `len(paper_ids)`（本批次实际新增数）
- 清单格式见 `<batch_output>` 部分
</kb_interaction>

<workflow>
## 工作流程

```
用户指定领域 ──→ 搜索论文 ──→ 下载 PDF ──→ 储存到知识库 ──→ 输出批次清单
     │                                                        │
     │                                                        ↓
     │                                               传递给 summarize
     │
继续学习 ──→ 读取最新反思 ──→ 解析"下一步计划" ──→ 确定搜索领域
                                              ↑         │
                                              │         ↓
                                              └── 反思循环 ← learning-reflection
```

**流程说明**：

1. **首次学习**（线性）：
   - 调用 `lib.kb.init_kb()` 初始化 → 用户指定领域 → 搜索 → 下载 → 调用 `lib.kb.add_paper_safe()` 储存 → 调用 `lib.kb.create_batch()` 创建批次 → 输出清单给 summarize

2. **继续学习**（环形）：
   - 调用 `lib.reflection_utils.read_latest_reflection()` → 调用 `lib.reflection_utils.parse_part4()` 解析计划 → 确定领域 → 搜索 → 下载 → 储存 → 输出清单
   - 反思模块生成的新计划会反馈到 fetch，形成学习循环

3. **领域调整**（迂回）：
   - fetch 过程中可能发现已有领域需要调整
   - 调用 `lib.kb` 相关函数更新领域结构
   - 继续当前批次的下载
</workflow>

<batch_output>
## 批次输出

**输出格式**：
```json
{
  "batch_id": "由 lib.kb.create_batch() 自动生成",
  "domain": "NLP/Transformer",
  "papers": [
    {
      "id": "arxiv:1706.03762",
      "title": "Attention Is All You Need",
      "path": "由 lib.config.get_paper_dir() 生成"
    }
  ],
  "total_count": 2
}
```

**生成方式**：
- batch_id：从 `lib.kb.create_batch()` 返回值中获取
- papers[].path：调用 `lib.config.get_relative_paper_dir(domain, title)` 获取相对路径字符串

**输出作用**：
1. **传递给 summarize 模块**：明确需要总结哪些论文，由 summarize 透传给 learning-reflection
</batch_output>

<workflow>
## 工作流程

```
用户指定领域 ──→ 搜索论文 ──→ 【去重校验】──→ 仅下载新论文 ──→ 储存到知识库 ──→ 输出批次清单
     │                              │                                                │
     │                              │ 去重：对比 kb.json                             ↓
     │                              │ 跳过已存在的                            传递给 summarize
     │                              │
继续学习 ──→ 读取最新反思 ──→ 解析"下一步计划" ──→ 确定搜索领域
                                              ↑         │
                                              │         ↓
                                              └── 反思循环 ← learning-reflection
```

**流程说明**：

1. **首次学习**（线性）：
   - 调用 `lib.kb.init_kb()` 初始化 → 用户指定领域 → 搜索 → **下载前去重** → 仅下载新论文 → 储存 → **文件夹前缀校验** → 调用 `lib.kb.create_batch()` 创建批次 → 输出清单给 summarize

2. **继续学习**（环形）：
   - 调用 `lib.reflection_utils.read_latest_reflection()` → 调用 `lib.reflection_utils.parse_part4()` 解析计划 → 确定领域 → 搜索 → **下载前去重** → 仅下载新论文 → 储存 → **文件夹前缀校验** → 输出清单
   - 反思模块生成的新计划会反馈到 fetch，形成学习循环

3. **领域调整**（迂回）：
   - fetch 过程中可能发现已有领域需要调整
   - 调用 `lib.kb` 相关函数更新领域结构
   - 继续当前批次的下载

**关键校验点**：
- 下载前去重：防止重复下载，避免浪费资源和时间
- 文件夹前缀校验：确保命名符合标准，便于后续管理和维护
- PDF文件大小检查：确保下载成功，避免0字节无效文件
</workflow>