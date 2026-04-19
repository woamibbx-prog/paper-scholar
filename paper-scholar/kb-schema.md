# 知识库模块

这是 paper-scholar skill 的知识库模块，负责存储和管理论文元数据、批次记录、领域信息和学习统计。

<module_overview>
## 模块概述
- **功能**：存储和管理论文元数据、批次记录、领域信息和学习统计
- **输入**：从 fetch、learning-reflection 模块更新的数据
- **输出**：提供给各模块查询的历史数据、领域关系、批次信息
- **协作**：作为系统的数据中心，支持所有模块的数据持久化
</module_overview>

<directory_structure>
根路径：`~/.paper-scholar/`

**首次初始化**：
当 `~/.paper-scholar/` 不存在时，由 fetch 模块首次运行时创建：
1. 创建 `~/.paper-scholar/kb/` 目录
2. 创建 `~/.paper-scholar/kb/kb-backups/` 目录
3. 创建 `~/.paper-scholar/kb/papers/` 目录
4. 创建 `~/.paper-scholar/kb/learning-progress/` 目录
5. 初始化 `kb.json`（空 papers、空 domains、空 batches、meta）

```
~/.paper-scholar/
├── kb/                         # 知识库目录
│   ├── kb.json                # 论文索引和元数据
│   ├── kb-backups/            # kb.json 备份
│   ├── papers/                # 论文存储（按领域分层）
│   │   └── NLP/
│   │       └── Transformer/
│   │           └── 论文标题/
│   │               ├── paper.pdf
│   │               └── summary.md
│   └── learning-progress/     # 学习反思
│       └── YYYY-MM-DD_HH-MM-SS.md
```

**文件夹命名规范**（重要！）：
- **领域文件夹**：以 `[领域]` 前缀标识，如 `[领域]Chain-of-Thought_Reasoning`
- **论文文件夹**：以 `[论文]` 前缀标识，如 `[论文] Attention Is All You Need`
- 前缀后有一个空格，紧跟名称
- 论文标题中的特殊字符替换为下划线
- 领域支持多级目录（父→子→孙），层级不限
- 任何层级都能放论文，不强制到最深层级
- 目的：一眼区分领域文件夹和论文文件夹，避免混淆

**每个论文文件夹标准结构**：
```
[论文] 论文标题/
├── paper.pdf        # PDF 全文
├── summary.md       # 中文结构化总结（800-1500字）
└── meta.json        # 元数据（标题、作者、摘要、arXiv ID）
```

**summary.md 必须使用中文撰写**，包含以下结构化章节：
- 摘要
- 研究背景与动机
- 核心方法
- 实验结果
- 局限性
- 应用价值
</directory_structure>

<kb_json_schema>
kb.json 是知识库的核心索引文件。

```json
{
  "domains": {
    "NLP": {
      "path": "papers/NLP/",
      "papers": ["arxiv:1706.03762"],
      "subdomains": ["Transformer"]
    },
    "NLP/Transformer": {
      "path": "papers/NLP/Transformer/",
      "papers": ["arxiv:1706.03762"],
      "parent": "NLP"
    }
  },
  "papers": {
    "arxiv:1706.03762": {
      "title": "Attention Is All You Need",
      "domain": "NLP/Transformer"
    }
  },
  "batches": {
    "2026-04-10_18-00-00": {
      "batch_id": "2026-04-10_18-00-00",       // fetch 创建
      "domain": "NLP/Transformer",                // fetch 创建
      "papers": ["arxiv:1706.03762"],             // fetch 创建
      "summary_file": "learning-progress/...",    // reflection 补全
      "next_domain": "NLP/Transformer/GPT"        // reflection 补全
    }
  },
  "meta": {
    "total_papers": 1,
    "total_domains": 2,
    "total_batches": 1,
    "learning_context": "已学习 NLP/Transformer 领域，核心发现：Transformer 架构颠覆了 RNN/CNN 序列建模方式，BERT 验证了预训练+微调范式。下一阶段将探索 GPT 系列模型。"
  }
}
```

**字段说明**：

**领域信息（domains）**：
- path：领域路径
- papers：包含的论文列表
- subdomains：子领域列表
- parent：父领域（如果有）

**论文信息（papers）**：
- title：论文标题（用于定位文件夹：空格转下划线）
- domain：所属领域

**批次信息（batches）**：
- batch_id：批次唯一标识
- domain：批次所属领域
- papers：包含的论文 ID 列表
- summary_file：反思文件路径（reflection 补全）
- next_domain：建议的下一个领域（reflection 补全）

**写入分工**：
- fetch 创建：batch_id, domain, papers
- learning-reflection 补全：summary_file, next_domain

**meta 写入分工**：
- fetch 更新：total_papers, total_domains, total_batches
- learning-reflection 更新：learning_context（累积学习上下文）

**统计信息（meta）**：
- total_papers：总论文数
- total_domains：总领域数
- total_batches：总批次数
- learning_context：累积学习上下文（3-5句，由 reflection 每轮更新，跨周期的"记忆桥梁"）
</kb_json_schema>

<domain_path_management>
新增领域时，判断新领域与已有领域的关系：

- 新顶级领域 → 在 papers/ 下建立新顶级目录
- 已有领域的子领域 → 在该领域下建立子目录
- 示例：已有 NLP/Transformer/，新开 GPT → 建立 NLP/Transformer/GPT/

**自动判断逻辑**：
1. 解析新领域的路径（如 "NLP/Transformer/GPT"）
2. 检查 domains 中的已有领域
3. 确定父领域，创建对应的目录结构
4. 更新 domains 中的父子关系
</domain_path_management>

<domain_restructure>
随着学习深入，对领域的认知会发生变化。可能先读了孙领域的论文，当时以为是父领域，学到后面才发现它只是更深层级的子领域。

**示例场景**：
1. 第一批：学了 Transformer，以为是父领域 → 放在 papers/Transformer/
2. 第三批：学了 NLP 基础，发现 Transformer 是 NLP 的子领域 → 需要调整为 papers/NLP/Transformer/
3. 后续：又发现 Vision Transformer 属于 CV → 需要重新归类

**调换流程**：
1. 创建新的目录结构
2. 移动已有论文到新路径
3. 更新 kb.json 中所有相关论文的 domain 字段
4. 删除旧的空目录
</domain_restructure>

<workflow>
## 工作流程

```
                        ┌──────────────────────────────┐
                        │          知识库 (kb)           │
                        │                              │
                        │  kb.json ←── 读取/更新 ──→ 各模块
                        │    ↑                           │
                        │    │                           │
                        │  写入                         读取
                        │    │                           │
                        │    ↓                           │
                        │  papers/    learning-progress/ │
                        └──────────────────────────────┘

各模块与知识库的交互时序：

fetch ──→ 写入新论文和批次信息（domains, papers, batches, meta）
         ↓
summarize ──→ 不更新知识库，只在论文目录下生成 summary.md
         ↓
learning-reflection ──→ 写入批次信息（batches, meta）
                    ──→ 写入反思文件到 learning-progress/
                    ──→ 可能触发领域重构
```

**交互说明**：

1. **fetch 阶段**：写入新论文、领域和批次信息
2. **summarize 阶段**：只生成文件，不更新 kb.json
3. **reflection 阶段**：写入批次信息和下一步计划，可能触发领域重构

**领域重构流程**（迂回）：
- reflection 发现领域关系变化 → 规划新结构 → 移动文件 → 更新 kb.json
- 重构后 fetch 按新结构继续下载
</workflow>