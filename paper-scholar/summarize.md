# 阅读总结模块

这是 paper-scholar skill 的阅读总结模块，负责读取 PDF 并生成结构化总结。

<module_overview>
## 模块概述
- **功能**：读取 PDF 并生成结构化总结
- **输入**：fetch 模块输出的批次论文清单
- **输出**：summary.md 文件 + 透传批次清单给 learning-reflection
- **协作**：接收 fetch 的批次清单，生成总结后将清单透传给 learning-reflection
</module_overview>

<module_rules>
## 模块规则

**PDF 解析规则**：
- 支持格式：PDF、PDF/A（加密文件需先解密）
- 页面限制：单篇论文最多 100 页
- 文本提取：优先提取文本内容，扫描件使用 OCR
- 字符编码：统一使用 UTF-8

**分析规则**：
- 结构化输出：必须包含所有指定章节
- 客观性：保持客观描述，避免主观评价
- 完整性：覆盖论文的核心贡献和方法
- 准确性：确保技术细节的准确性

**总结生成规则**：
- 字数限制：每篇总结 800-1500 字
- 语言：**必须使用中文**（这是硬性要求，不可跳过）
- 格式：使用 Markdown 格式
- 文件名：summary.md（固定名称）
- 结构：必须包含以下固定章节标题（一字不差）：
  - `## 摘要`（200字以内概述）
  - `## 研究背景与动机`（为什么做这个研究）
  - `## 核心方法`（关键技术和方法）
  - `## 实验结果`（量化结果和对比）
  - `## 局限性`（不足之处）
  - `## 应用价值`（实际意义）
- **禁止格式**：`## 一、研究背景`、`## 二、核心方法`、`## 1. 摘要` 等编号格式

**summary.md 模板（必须严格遵守）**：
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

**常见错误及修正**：
- ❌ `## 一、研究背景` → ✅ `## 研究背景与动机`
- ❌ `## 二、核心方法` → ✅ `## 核心方法`
- ❌ `## 3. 实验结果` → ✅ `## 实验结果`
- ❌ `## 四、创新点` → ✅ `## 实验结果`
- ❌ `## 五、局限性` → ✅ `## 局限性`
- ❌ `## 六、应用价值` 或 `## 七、应用价值` → ✅ `## 应用价值`

**内容要求**：
- 摘要：简洁概括核心贡献和创新点，200字以内
- 研究背景与动机：说明研究背景、问题定义、研究动机
- 核心方法：详细描述关键技术和方法，包括算法、架构、实验设置
- 实验结果：提供量化结果和对比分析
- 局限性：诚实地指出不足之处和待解决问题
- 应用价值：说明实际应用场景和意义

**错误处理**：
- 解析失败：记录错误，跳过该论文
- 内容异常：无法解析时标记为 "unavailable"
- 格式错误：自动修正格式问题
- 重复总结：检查已有文件，避免重复生成
</module_rules>

<module_coordination>
## 模块协作

**summarize 模块职责**：
- 读取本地 PDF 文件
- 分析论文内容
- 生成结构化总结
- 写入 summary.md

**协作流程**：
```
fetch → summarize → learning-reflection
```

**输入格式**：
- 批次论文清单：从 fetch 模块输出，包含论文 ID、标题、路径
- 论文文件夹路径：kb/papers/{domain}/{paper_title}/

**知识库协作**：
- 总结生成前：从批次清单获取论文路径，检查已有总结避免重复
- 总结完成后：在论文文件夹下生成 summary.md，不更新 kb.json
</module_coordination>

<implementation>
## 分析内容
1. **基本信息**：标题、作者、发表时间、期刊/会议
2. **研究背景**：领域背景和问题定义
3. **核心方法**：关键技术、算法、模型架构
4. **创新点**：主要贡献和突破
5. **实验结果**：数据集、评估指标、性能表现
6. **局限性**：不足之处和待解决问题
7. **应用价值**：实际应用场景和意义
</implementation>

<workflow>
## 处理流程

**步骤1：准备输入**
- 接收 fetch 模块输出的批次论文清单
- 根据清单中的路径定位每篇论文
- 调用 `lib.config.get_summary_path(domain, title)` 检查是否已有总结，避免重复

**步骤2：读取 PDF**
- 使用 Claude Read 工具直接读取 PDF 文件
- 论文 PDF 路径：`lib.config.get_pdf_path(domain, title)`

**步骤3：内容分析**
- Agent 深入阅读和理解论文
- 提取关键技术信息
- 分析创新点和贡献

**步骤4：生成总结**
- 根据结构化模板生成总结
- 确保内容准确和全面
- 保持客观和学术性

**步骤5：写入文件并透传**
- 调用 `lib.config.get_summary_path(domain, title)` 获取写入路径
- 将总结写入该路径
- 将批次清单透传给 learning-reflection 模块
</workflow>

<batch_processing>
## 批次处理示例

**输入示例**（来自 fetch 模块）：
```json
{
  "batch_id": "2026-04-11_14-30-00",
  "domain": "NLP/Transformer",
  "papers": [
    {
      "id": "arxiv:1706.03762",
      "title": "Attention Is All You Need",
      "path": "kb/papers/NLP/Transformer/Attention_Is_All_You_Need/"
    },
    {
      "id": "arxiv:1810.04805",
      "title": "BERT: Pre-training of Deep Bidirectional Transformers",
      "path": "kb/papers/NLP/Transformer/BERT/"
    }
  ]
}
```

**处理过程**：
1. 读取第一批论文：Attention Is All You Need
   - 生成：`kb/papers/NLP/Transformer/Attention_Is_All_You_Need/summary.md`
2. 读取第二批论文：BERT
   - 生成：`kb/papers/NLP/Transformer/BERT/summary.md`
3. 返回处理结果给 learning-reflection 模块
</batch_processing>

<example_output>
## 示例输出：Attention Is All You Need - summary.md

```markdown
# Attention Is All You Need - 总结

## 基本信息
- **标题**: Attention Is All You Need
- **作者**: Ashish Vaswani, Noam Shazeer, et al.
- **发表**: 2017 NIPS/NeurIPS
- **引用量**: 50000+
- **下载量**: 30000+

## 研究背景
- **领域**: 自然语言处理
- **问题**: 传统序列模型（RNN/LSTM）并行化困难，长距离依赖捕捉能力弱
- **目标**: 提出全新的基于注意力机制的序列建模方法

## 核心方法
- **Transformer 架构**: 完全基于 Self-Attention，摒弃 RNN/CNN
- **多头注意力**: 8 个并行注意力头，捕捉不同子空间信息
- **位置编码**: 使用正弦和余弦函数编码位置信息
- **编码器-解码器**: 6 层编码器 + 6 层解码器堆叠
- **前馈网络**: 每个子层后接位置前馈网络

## 创新点
1. **纯注意力机制**: 首次证明注意力机制可以独立完成序列建模
2. **并行计算**: 相比 RNN 的顺序计算，完全并行化，训练效率大幅提升
3. **长距离依赖**: 自注意力机制直接捕捉任意位置间的依赖关系
4. **可扩展性**: 模型易于扩展，为后续大规模模型奠定基础

## 实验结果
- **数据集**: WMT 2014 English-German translation
- **BLEU**: 28.4，比当时最佳结果提高 2.0
- **训练时间**: 在 8 个 P100 GPU 上训练 3.5 天
- **推理速度**: 每秒处理 27k 词对

## 局限性
- **计算复杂度**: O(n²) 复杂度，长文本处理困难
- **内存消耗**: 自注意力矩阵需要 O(n²) 内存
- **训练成本**: 需要大量计算资源，训练成本高
- **位置依赖**: 位置编码固定，无法自适应不同序列长度

## 应用价值
- **NLP 革命**: 成为现代 NLP 的基础架构
- **预训练模型**: 为 BERT、GPT 等提供基础
- **多模态扩展**: 扩展到语音、视觉等模态
- **工业应用**: Google 翻译、BERT 等实际应用
```
</example_output>
