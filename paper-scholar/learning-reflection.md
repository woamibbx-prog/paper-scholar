# 学习反思模块

这是 paper-scholar skill 的学习反思模块，负责生成批次学习反思和下一步学习计划。

<module_overview>
## 模块概述
- **功能**：生成批次学习反思和下一步计划
- **输入**：本批次所有 summary.md + 历史反思
- **输出**：学习反思文件 + 下一步建议 + 更新后的知识库
- **协作**：与知识库协作记录反思，指导 fetch 模块的下一步
</module_overview>

<module_rules>
## 模块规则

**反思生成规则**：
- 深度分析：必须进行 3-5 句的深度技术分析，禁止一句话概括
- 历史对比：结合至少 1 篇历史论文进行比较
- 领域判断：明确领域关系（父子/兄弟/全新）
- 计划制定：提供具体可行的下一步学习方向
- 格式刚性：PART 4 必须使用【标签】格式，否则 parse_part4 无法正确解析

**PART 2 深度分析要求**：
- 不得写成一句话概括，如"本批次学习了X和Y两篇论文"
- 必须分析论文之间的技术关联、领域发展趋势、关键技术演进脉络
- 需要展示对论文的深度理解，而不是简单罗列
- 至少 3-5 句，每句都要有实质性内容

**PART 4 标签格式要求**：
- 必须使用【】格式的标签
- 标签内容必须是：`【继续当前领域】` 或 `【转向相关领域】` 或 `【或转向相关领域】`
- 不得使用其他格式，如`「继续当前领域」`、`【继续】`等

**输入处理规则**：
- 单篇论文：生成基础反思
- 批量论文（≥3篇）：进行领域级深度分析
- 历史反思：参考前 2 次反思（前面只有一次反思就只读那一次）
- 空历史：生成首次反思，不进行历史对比
- 输入来源：summarize 透传的批次清单 + `kb/papers/{领域}/{论文}/summary.md` + `~/.paper-scholar/kb/learning-progress/` 中的历史反思

**输出格式规则**：
- 文件名：YYYY-MM-DD_HH-MM-SS.md（精确到秒）
- 存储位置：~/.paper-scholar/kb/learning-progress/
- 结构：必须包含所有 4 个 PART
- 字数：总字数 800-1200 字

**质量控制规则**：
- 技术准确性：确保技术描述正确
- 逻辑一致性：前后分析保持一致
- 可执行性：下一步计划要具体可行
- 客观性：避免个人偏好影响判断

**learning_context 更新规则**：
- 每次反思完成后，必须更新 kb.json meta.learning_context
- 内容：3-5 句话，涵盖已学领域、关键技术脉络、当前方向
- 目的：作为跨周期的"记忆桥梁"，让新上下文能快速恢复全局认知
- 格式示例："已学习 A 领域和 B 领域，核心发现是 X。当前在学 C 领域，下一阶段将探索 D。"
- **更新时机**：在 complete_batch 之后、周期结束前
</module_rules>

<module_coordination>
## 模块协作

**协作流程**：
```
summarize → learning-reflection → 更新知识库 → fetch(下一步)
```

**协作步骤**：
1. **输入阶段**：
   - 接收 summarize 透传的批次论文清单（包含 batch_id、论文 ID、路径）
   - 从批次清单中提取 `batch_id`，后续调用 `complete_batch` 时需要
   - 调用 `lib.reflection_utils.read_latest_reflection()` 读取最新历史反思（返回 None 则为首次）
   - 从 `lib.kb.load_kb()` 获取学习进度和领域分布

2. **处理阶段**：
   - 读取本批次所有 summary.md（通过批次清单中的路径）
   - 深度分析论文内容
   - 结合历史进行对比
   - 生成领域判断和学习计划

3. **输出阶段**：
   - 调用 `lib.reflection_utils.write_reflection(content)` 写入反思文件
     - 返回值直接是 kb.json 所需的相对路径格式 `"learning-progress/YYYY-MM-DD_HH-MM-SS.md"`
   - 调用 `lib.kb.complete_batch(kb, batch_id, summary_file, next_domain)` 补全批次信息
     - batch_id = 从透传的批次清单中获取（fetch 生成，summarize 原样传递）
     - summary_file = write_reflection 的返回值
   - 调用 `lib.kb.update_learning_context(kb, context)` 更新 learning_context
   - **🔴 新增**：调用 `lib.self_repair.run_self_repair(kb, batch_id, summary_file)` 执行自修复
     - 检查执行结果
     - 检测漏洞
     - 自动修复数据不一致
     - 清理垃圾数据
   - **🔴 新增**：调用 `lib.kb.clear_task_status()` 清理任务状态

4. **与 fetch 模块的协作**：
   - fetch 调用 `lib.reflection_utils.parse_part4()` 读取学习计划
   - 根据解析结果中的 keywords 搜索论文
   - 自动创建对应的目录结构

**错误处理**：
- `ReflectionParseError`（parse_part4 解析失败）：回退到手动阅读 PART 4 原文，自行理解计划内容
- `BatchNotFoundError`（complete_batch 找不到批次）：检查 batch_id 是否正确，确认 fetch 已调用 create_batch
- `KBNotFoundError`（load_kb 失败）：不应发生在此阶段，如果发生说明流程出错

**知识库更新示例**：
```json
{
  "batches": {
    "2026-04-11_14-30-00": {
      "batch_id": "2026-04-11_14-30-00",
      "domain": "NLP/Transformer",
      "papers": ["arxiv:1706.03762", "arxiv:1810.04805"],
      "summary_file": "learning-progress/2026-04-11_14-30-00.md",
      "next_domain": "NLP/Transformer/GPT"
    }
  }
}
```

**调用时机**：
- 批次论文全部总结完成
- 需要决定下一步方向
- 需要更新领域认知
</module_coordination>

<workflow>
## 工作流程

```
本批次所有 summary.md ──→ lib.reflection_utils.read_latest_reflection() ──→ 深度分析
                                                                              │
                                                                              ↓
                                                                      生成反思内容（4个PART）
                                                                              │
                            ┌──────────────────────┬─────────────────────────┤
                            ↓                      ↓                         ↓
                  write_reflection()      complete_batch()          update_learning_context()
                  写入反思文件             补全批次信息               更新跨周期记忆
                            │                      │                         │
                            └──────────────────────┴─────────────────────────┘
                                                    │
                                                    ↓
                                              fetch 模块调用
                                              parse_part4() 解析计划
                                                    │
                                                    ↓
                                              新一轮学习循环 ←──┘
```

**循环机制**：
- 反思模块是学习循环的核心枢纽
- 每次反思决定下一轮学习方向
- 每次调用 `lib.kb.update_learning_context()` 更新跨周期记忆桥梁
- 随着学习深入可能触发领域重构
</workflow>


<reflection_structure>
按以下结构撰写反思：

## PART 1: 本批次论文学习

对每篇论文分别列出：

- **论文标题**
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

**计划制定原则**：
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
</reflection_structure>

<example>
# 学习反思 2026-04-10

## PART 1: 本批次论文学习

- **Attention Is All You Need**
  - 技术与创新点：提出 Transformer 架构，完全基于 Self-Attention 机制，摒弃 RNN/CNN；并行计算效率高
  - 不足：计算复杂度 O(n²)，长文本处理困难；训练成本高

- **BERT: Pre-training of Deep Bidirectional Transformers**
  - 技术与创新点：提出预训练+微调范式；双向上下文建模；GLUE 基准刷榜
  - 不足：参数量大，推理慢；微调需要大量标注数据；MASK 机制导致预训练-微调不一致

## PART 2: 结合历史反思

- 本批次在领域认知上的进展：
  本批次的两篇论文标志着 NLP 领域的一次范式转变。Attention Is All You Need 彻底颠覆了 RNN/CNN 的序列建模方式，证明了纯注意力机制可以在更少训练时间下达到更好的效果。而 BERT 则在此基础上，开创了"预训练+微调"的新范式，让 NLP 任务从 task-specific 模型走向通用模型。
  两篇论文的关系是：Transformer 提供了底层架构，BERT 验证了该架构在预训练场景下的强大能力。这预示着未来 NLP 的核心方向将是——更大规模的预训练模型 + 更高效的微调策略。
- 已学习领域：Deep Learning 基础 / NLP 基础 / Transformer 架构 / BERT 预训练模型
- 下一步领域：继续深入 Transformer 生态，学习 GPT 系列

## PART 3: 领域判断

- 如果选择学习 GPT：GPT 与 BERT 是兄弟关系，同属 Transformer 预训练模型家族，但 GPT 侧重单向语言模型
- 如果继续学本领域：继续存放在 `kb/papers/NLP/Transformer/`
- 如果新开 GPT 领域：存放到 `kb/papers/NLP/Transformer/GPT/`

## PART 4: 下一步学习计划

【转向相关领域】
- 新领域：GPT 系列模型
- 学习路径：从 GPT-1 → GPT-2 → GPT-3
- 基础要求：需要先了解自回归语言模型

**本批次 learning_context 更新**（写入 kb.json meta）：
```
"learning_context": "已学习 NLP/Transformer 领域 2 篇论文。核心发现：Transformer 架构颠覆了 RNN/CNN 序列建模方式，BERT 验证了预训练+微调范式。当前方向：探索 GPT 系列模型的自回归语言模型。"
```
</example>
