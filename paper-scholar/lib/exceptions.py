"""自定义异常类型。

为不同错误场景提供明确的异常类型，
避免所有错误都抛通用 Exception。
"""


class PaperScholarError(Exception):
    """paper-scholar 基础异常"""
    pass


class KBNotFoundError(PaperScholarError):
    """知识库不存在（kb.json 缺失）"""
    pass


class PaperExistsError(PaperScholarError):
    """论文已存在于知识库中（重复添加）"""
    pass


class BatchNotFoundError(PaperScholarError):
    """批次不存在（补全时找不到对应 batch_id）"""
    pass


class ReflectionParseError(PaperScholarError):
    """反思文件解析失败（找不到 PART 4 或格式错误）"""
    pass
