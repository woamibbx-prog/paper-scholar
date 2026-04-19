---
name: Paper Scholar
slug: paper-scholar
version: 2.1.0
homepage: https://github.com/openclaw/paper-scholar
description: "自主循环学习学术论文的 Skill。通过搜索、获取、总结、反思的完整流程，实现系统性学术研究。这是一个自主学习闭环系统，每个周期自主决定下一步学什么，通过反思文件和知识库索引在周期之间保持连续性。"
changelog: "全面重构：标准化所有刚性规范、添加元数据格式、固化多轮循环经验、强化跨周期一致性保证。所有规范已从STANDARDIZATION_GUIDE.md整合到主文档。"
metadata: {"clawdbot":{"emoji":"📚","requires":{"bins":["py"],"pip":["arxiv"]},"os":["linux","darwin","win32"],"configPaths":["~/.paper-scholar/"]}}
---

## Quick Reference

| 场景 | 动作 | 入口文件 |
|------|------|----------|
| 用户指定领域 | 直接搜索该领域论文 | fetch.md |
| 继续学习 | 读取最新反思的 PART 4 计划 | fetch.md → learning-reflection.md |
| 周期性执行 | 按恢复协议恢复，然后继续学习 | SKILL.md（本文件） |
| 研究需求 | 搜索特定主题论文 | fetch.md |

## What This Skill Does

Paper Scholar 在四个维度上运作：

1. **论文获取**：根据领域或反思计划搜索 arXiv，按被引量、下载量、时效性筛选，批量下载 PDF 并按领域树形结构储存
2. **深度阅读**：逐篇解析 PDF，生成 800-1500 字的结构化总结（基本信息、研究背景、核心方法、创新点、实验结果、局限性、应用价值）
3. **学习反思**：结合本批次总结和历史反思，进行领域级深度分析，判断领域关系（父子/兄弟/全新），生成下一步学习计划
4. **知识管理**：维护 JSON 索引（领域树、论文索引、批次记录）和累积学习上下文，确保跨周期的连续性

## Core Execution Loop

1. **确定学习方向**
   - 用户指定领域 → 直接搜索
   - "继续学习" / 周期性恢复 → 读取最新反思的 PART 4 计划
   - 周期性首次启动（无知识库）→ 需要用户提供起始领域

2. **获取论文**（fetch 模块）
   - 搜索 arXiv → 筛选 → **下载前去重**（调用 `lib.kb.check_duplicate_papers()`） → **仅下载新论文** → 储存到知识库
   - **创建后立即校验**文件夹前缀
   - 更新 kb.json（papers, domains, batches, meta）
   - 输出批次清单

3. **阅读总结**（summarize 模块）
   - 接收批次清单 → 逐篇解析 PDF → 生成 summary.md（800-1500字，固定章节标题）
   - 透传批次清单给反思模块

4. **学习反思**（learning-reflection 模块）
   - 读取本批次所有总结 + 历史 1-2 次反思
   - **生成反思文件**（4 个 PART，PART 2 深度分析 3-5 句，PART 4 【标签】格式）
   - 补全 kb.json + 更新 learning_context

5. **循环或结束**
   - 周期性执行 → 等 20 分钟 → 按恢复协议重启
   - 手动执行 → 等用户说"继续学习"

6. **周期结束前自检**（刚性要求）
   - 运行标准化校验：`py -3 ~/.openclaw/workspace/scripts/paper-scholar-normalize.py`
   - 检查修复结果 → 直到所有检查通过才算周期完成
   - 输出反思文件供老大审阅

## Core Principle

反思驱动学习。每个周期结束时基于当前理解主动规划下一步方向，不被动等待指令。

## ⚠️ 刚性标准化规范（必须严格遵守）

**以下规范是硬性要求，每次执行必须完全遵守，不得有任何偏差。违反规范将导致学习循环不稳定，无法保持跨周期的标准化和一致性。**

### 文件夹命名

| 类型 | 格式 | 示例 |
|------|------|------|
| 领域文件夹 | `[领域]英文名称` | `[领域]Chain-of-Thought_Reasoning` |
| 论文文件夹 | `[论文] 论文英文标题` | `[论文] Attention Is All You Need` |

**规则：**
- 前缀后论文有一个空格，领域无空格：`[论文] ` vs `[领域]`
- 标题仅使用英文，不添加中文翻译（包括括号中的中文）
- 特殊字符替换为下划线（如空格、冒号等）
- 示例：`[论文] WizardLM_ Empowering Large Language Models`
- **禁止格式**：`[论文] Title (中文翻译)`、`[论文] Title_标题`、`[领域] 名称 (English)`

**创建后立即校验（刚性要求）：**
- 每次创建新文件夹后，必须立即检查前缀是否正确
- 领域文件夹 → 必须以 `[领域]` 开头，如 `[领域]Efficient_Inference`
- 论文文件夹 → 必须以 `[论文] ` 开头（注意空格），如 `[论文] Attention Is All You Need`
- 如果发现缺少前缀，**立即重命名修复**，不可留到自检阶段

### summary.md 格式

每个 summary.md **必须使用中文**撰写，包含以下**固定章节标题**（一字不差）：

```markdown
# 论文中文标题

**论文ID**: arxiv:XXXX.XXXXX

## 摘要
（200字以内概述）

## 研究背景与动机
（为什么做这个研究）

## 核心方法
（关键技术和方法）

## 实验结果
（量化结果和对比）

## 局限性
（不足之处）

## 应用价值
（实际意义）

---
*由 Paper Scholar 自动总结*
```

**禁止的标题格式：** `一、`、`二、`、`1.`、`2.` 等编号格式。只用 `## 标准名`。

**常见错误示例：**
- ❌ `## 一、研究背景` → ✅ `## 研究背景与动机`
- ❌ `## 二、核心方法` → ✅ `## 核心方法`
- ❌ `## 3. 实验结果` → ✅ `## 实验结果`
- ❌ `## 四、创新点` → ✅ `## 实验结果`
- ❌ `## 五、局限性` → ✅ `## 局限性`
- ❌ `## 六、应用价值` 或 `## 七、应用价值` → ✅ `## 应用价值`

**字数要求：** 每篇总结 800-1500 字，避免过短或过长。

### 反思文件命名

格式：`YYYY-MM-DD_HH-MM-SS.md`（精确到秒）

**禁止格式：** `reflection_YYYYMMDD.md`、`batch_xxx.md`、`round-XX-reflection.md` 等任何其他格式。

**正确示例：**
- ✅ `2026-04-17_14-30-22.md`
- ❌ `reflection_20260417_143022.md`
- ❌ `batch_20260417.md`
- ❌ `round-42-reflection.md`

### 反思文件结构

必须包含 4 个 PART，每个 PART 有实质内容（不能是占位符）：

- **PART 1**: 每篇论文的技术创新点 + 不足（非空泛描述）
- **PART 2**: 3-5 句深度技术关联分析（**非一句话概括**）
- **PART 3**: 领域关系判断和存储路径建议
- **PART 4**: 使用【标签】格式的具体下一步计划

**PART 结构规范：**

```markdown
## PART 1: 本批次论文学习

- **论文标题1**
  - 技术与创新点：核心技术和创新点
  - 不足：局限性或待解决的问题

- **论文标题2**
  - 技术与创新点：核心技术和创新点
  - 不足：局限性或待解决的问题

## PART 2: 结合历史反思

- **本批次在领域认知上的进展或调整**：（重要：这部分是整篇反思的核心，不是一句话概括。你需要深入分析本批次所有论文之间的技术关联、领域发展趋势、关键技术演进脉络。至少写 3-5 句，展示你对这些论文的深度理解。）
- 已学习领域（累计）
- 下一步领域：继续学习当前领域 还是 转向相关领域

## PART 3: 领域判断

- 如果新开领域：新领域与已有领域的关系（父子/兄弟/全新）
- 建议存储路径：根据领域关系，建议存放到哪个路径下，或是否需要新建文件夹

## PART 4: 下一步学习计划

**计划制定原则：**
- **具体性**：明确具体的学习方向，避免模糊表述
- **可执行性**：下一批次可以立即执行的计划
- **连贯性**：基于本批次的学习进展提出
- **格式必须性**：必须使用下面的【标签】格式，因为 fetch 模块的 `lib.reflection_utils.parse_part4()` 通过正则匹配这些标签来提取结构化信息

**计划格式**（必须严格遵循）：
```
【继续当前领域】
- 具体方向：如 Transformer 的 FlashAttention 优化
- 学习目标：理解原理、实现、优化效果

【或转向相关领域】（如果选择继续，不要写这一段；如果选择转向，不要写上一段）
- 新领域：如 GPT 系列模型
- 学习路径：从 GPT-1 → GPT-2 → GPT-3
- 基础要求：需要先了解自回归语言模型
```
```

**PART 2 内容深度要求：**
- 不得写成一句话概括，如"本批次学习了X和Y两篇论文"
- 必须进行深度技术分析，至少 3-5 句
- 需要分析论文之间的技术关联、领域发展趋势、关键技术演进脉络
- 展示对论文的深度理解，而不是简单罗列

**PART 4 标签格式要求：**
- 必须使用【】格式的标签
- 标签内容必须是：`【继续当前领域】` 或 `【转向相关领域】` 或 `【或转向相关领域】`
- 不得使用其他格式，如`「继续当前领域」`、`【继续】`等

### 每个论文文件夹标准内容

```
[论文] 标题/
├── paper.pdf      # PDF 全文（必需）
├── summary.md     # 中文结构化总结（必需）
└── meta.json      # 元数据（必需，含 title/id/abstract/authors/published）
```

**文件完整性要求：**
- paper.pdf：必须存在且大小 > 0 字节（0字节PDF视为无效，需重新下载）
- summary.md：必须存在且符合标准化格式
- meta.json：必须存在且包含必需字段

**禁止文件：**
- extracted*.txt：临时提取文件，应删除
- 其他中间文件：应清理

### 下载前去重校验（刚性要求）

**每次下载论文 PDF 之前，必须先与 kb.json 中已有论文进行对比，禁止重复下载。**

- 下载前调用 `lib.kb.check_duplicate_papers(kb, candidates)` 进行批量去重
- `candidates` 为待下载论文列表，每项含 `id`（arxiv ID）和 `title`
- 函数返回 `(new_papers, duplicates)`，仅对 `new_papers` 执行下载
- `duplicates` 中的论文需在日志中明确列出（ID + 标题），标明「已跳过：已存在于知识库」
- **禁止**先下载再靠 `add_paper_safe` 跳过——必须在网络请求前就拦截
- 如果所有候选论文都是重复的（无新论文），跳过下载和后续步骤，直接进入反思模块告知无新论文

**去重逻辑：**
- 优先按 arxiv ID 精确匹配
- 其次按标题模糊匹配（防止同一论文 ID 不同但实际是同一篇）
- 标题匹配忽略大小写和前后空格

**处理流程：**
```
候选论文列表 → check_duplicate_papers() → (new_papers, duplicates)
                                           ↓                      ↓
                                    仅下载 new_papers        在日志中列出 duplicates
                                           ↓
                                    如果 new_papers 为空 → 直接进入反思模块
```

### 周期结束前自检（刚性要求）

**每个周期结束前，必须按顺序执行：**

1. **运行标准化校验**：`py -3 ~/.openclaw/workspace/scripts/paper-scholar-normalize.py`
2. **检查修复结果**：
   - 如果输出显示 `All checks passed` → 周期完成
   - 如果发现 `FIXED` 或 `BAD` 项 → **立即修复后重新运行校验，直到所有检查通过才算周期完成**
3. **输出反思文件**：将本次生成的反思文件完整输出作为回复内容，供老大审阅

**自检内容**（标准化校验脚本会检查）：
- [1] 反思文件命名是否为 YYYY-MM-DD_HH-MM-SS.md
- [2] 文件夹命名是否有正确的前缀（[领域] 或 [论文]）
- [3] summary.md 格式是否符合标准（固定章节标题，无编号格式）
- [4] 是否有垃圾数据（0字节PDF、临时文件、空目录）
- [5] kb.json 路径是否与实际文件系统一致
- [6] 所有路径是否可解析

**自检流程：**
```
生成反思文件 → 运行标准化校验 → 检查结果
                                           ↓
                                   发现问题？→ 立即修复
                                           ↓
                                     重新运行校验
                                           ↓
                                   All checks passed? → Yes → 周期完成
                                                     |
                                                     No → 继续修复
```

## 恢复协议

当在新上下文中恢复执行时（如周期性任务的第二轮），按以下步骤恢复：

1. **读取本文件**（SKILL.md）：了解整体流程和模块职责
2. **检查知识库**：调用 `lib.kb.load_kb()`
   - **KBNotFoundError**（首次运行 / 知识库不存在）：
     - 如果用户说的是"继续学习"而非具体领域 → 告知用户"首次运行需要指定学习领域，请告诉我你想学什么"
     - 如果用户指定了领域 → 调用 `lib.kb.init_kb()` 初始化知识库
   - **成功**（继续学习）：从返回的 kb 字典中读取
     - `meta.learning_context`：累积学习上下文（跨周期的"记忆桥梁"，3-5 句概括所有历史）
     - `domains`：已学习的领域分布
     - `papers`：已学习的论文列表
     - `batches`：历史批次记录
3. **读取最新反思**：调用 `lib.reflection_utils.read_latest_reflection()`
   - 返回 None（首次运行，无反思）→ 按用户指定领域搜索
   - 返回反思内容 → 调用 `lib.reflection_utils.parse_part4(content)` 提取下一步计划
4. **开始执行**：根据解析出的计划，进入 fetch 模块

**为什么需要恢复协议：**
- 每个周期可能是新的上下文窗口，没有历史记忆
- kb.json 的 `learning_context` 是跨周期的"记忆桥梁"
- 只需读 3 个文件（SKILL.md + kb.json + 最新反思）即可完全恢复
- 首次运行时只需用户提供一个起始领域即可

## 模块协作

**数据传递链：**
```
fetch(批次清单) → summarize(透传清单) → reflection → 反思文件 → fetch(读取PART4) → 循环
```

**代码层（lib/）**：每个模块的机械操作（路径计算、kb.json 读写、反思解析）通过 `lib/` Python 库执行。各模块 .md 文件中标注了每个步骤应调用的 lib 函数。

**知识库更新分工：**

| 阶段 | 写入内容 |
|------|----------|
| fetch | papers, domains, batches(创建: batch_id, domain, papers), meta |
| summarize | 只生成 summary.md，不更新知识库 |
| reflection | batches(补全: summary_file, next_domain), meta.learning_context |

**示例学习路径：**
```
批次1: Transformer → 反思建议学习 GPT
批次2: GPT → 反思建议深入优化
批次3: 优化 → 反思建议新领域...
```

## 知识库结构

**路径：** `~/.paper-scholar/`

```
~/.paper-scholar/
├── kb/
│   ├── kb.json                    # 知识库索引
│   └── kb-backups/                # 备份
├── papers/                        # 论文存储（主目录）
│   └── {大领域}/
│       └── [领域]{子领域}/         # 子领域文件夹扁平化，直接挂在大领域下
│           └── [论文] 标题/
│               ├── paper.pdf
│               ├── summary.md
│               └── meta.json
└── learning-progress/             # 学习反思（主目录）
    └── {大领域}/
        └── YYYY-MM-DD_HH-MM-SS.md
```

**路径规范：**
- `papers/` 和 `learning-progress/` 直接在 `~/.paper-scholar/` 下（主存储）
- `kb/` 只存放 `kb.json` 和 `kb-backups/`（索引和备份）
- 子领域文件夹**扁平化**：`papers/ULM/[领域]深度学习定位与检测/[论文]xxx/`
- **禁止**嵌套两层领域文件夹：`papers/ULM/[领域]ULM.../[领域]xxx/` ❌
- 论文文件夹直接放在子领域文件夹内，不额外嵌套

**kb.json 核心结构：**

| 字段 | 说明 | 写入者 |
|------|------|--------|
| domains | 领域树（path, papers, subdomains, parent） | fetch |
| papers | 论文索引（title, domain） | fetch |
| batches | 批次记录（fetch 创建部分，reflection 补全） | fetch + reflection |
| meta | 统计信息 + learning_context（跨周期记忆桥梁） | fetch + reflection |

**论文 ID 格式：** arXiv ID `arxiv:YYMM.NNNNN`（如 `arxiv:1706.03762`）

## What This Is Not

- 不是搜索引擎前端 —— 自主决定搜索方向
- 不是一次性工具 —— 通过反思循环实现持续学习
- 不是论文收藏器 —— 每篇论文都有深度总结和领域分析
- 不是固定课程 —— 学习路径由反思动态决定

## 模块文件

| 文件 | 职责 |
|------|------|
| [kb-schema.md](kb-schema.md) | 知识库数据结构、JSON schema、领域管理规则 |
| [fetch.md](fetch.md) | 搜索、筛选、下载、储存、批次输出 |
| [summarize.md](summarize.md) | PDF 解析、结构化总结、批次透传 |
| [learning-reflection.md](learning-reflection.md) | 深度分析、领域判断、学习计划、learning_context 维护 |
| [STANDARDIZATION_GUIDE.md](STANDARDIZATION_GUIDE.md) | 详细标准化指南、经验教训总结、校验脚本说明 |
| [self-repair.md](self-repair.md) | 自修复模块、检查执行结果、检测漏洞、自动修复数据不一致 |

**代码层（lib/）：**

| 文件 | 职责 |
|------|------|
| [lib/config.py](lib/config.py) | 路径常量（KB_ROOT、get_paper_dir、get_latest_reflection） |
| [lib/exceptions.py](lib/exceptions.py) | 自定义异常（KBNotFoundError、PaperExistsError 等） |
| [lib/kb.py](lib/kb.py) | 知识库 CRUD（load_kb、add_paper_safe、create_batch、complete_batch、check_duplicate_papers） |
| [lib/reflection_utils.py](lib/reflection_utils.py) | 反思操作（write_reflection、parse_part4、read_latest_reflection） |
| [lib/self_repair.py](lib/self_repair.py) | 自修复操作（run_self_repair、检查和修复函数、任务状态跟踪） |

## Outcome

- 自主决定学习方向，不依赖用户逐步指定
- 在领域树中组织论文，随着认知深入动态调整分类
- 跨周期保持连续性，通过 learning_context 恢复全局认知
- 通过反思驱动学习循环，每轮都在深化对领域的理解
- 刚性标准化确保无论开启多少个新的循环任务，都能保持始终如一的执行质量

## Keywords

ai-agent, academic-research, paper-learning, arxiv, knowledge-base, self-directed-learning, reflection-loop, standardization, automated-research

## 版本历史

- **v2.0.0** (2026-04-17): 全面重构，标准化所有刚性规范，固化多轮循环经验，强化跨周期一致性保证
- **v1.0.0** (2026-04-11): 初始版本，实现基础学习循环功能
