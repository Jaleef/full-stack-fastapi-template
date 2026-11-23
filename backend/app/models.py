"""数据库模型。

一次分析（analysis）是根记录，其余表都通过 analysis_id 挂在它下面，删除分析时级联清理。
表之间的依赖关系：

    analysis 1 ──< document              上传的两份源文档（需求 + 设计）
    analysis 1 ──< parse_decision        每个候选块的判定结果（解析审计）
    analysis 1 ──< requirement_unit      需求单元（可追溯容器）
    analysis 1 ──< atomic_requirement    原子需求（参与匹配的最小断言）
    analysis 1 ──< design_element        设计要素
    analysis 1 ──< mapping               原子与要素的判定
    analysis 1 ──< finding               规则或语义产生的问题
    analysis 1 ──0..1 analysis           复检时 previous_id 指向上一次分析

    requirement_unit 1 ──< atom_source >── 1 atomic_requirement
    atomic_requirement 1 ──< mapping >── 1 design_element

    llm_cache                            独立缓存表，不依赖 analysis

读表顺序建议：analysis → document → parse_decision → requirement_unit →
atomic_requirement → atom_source → design_element → mapping → finding。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Index
from sqlmodel import Field, SQLModel

from app.core.config import settings


def utcnow() -> datetime:
    """返回当前 UTC 时间。"""
    return datetime.now(UTC)


class Analysis(SQLModel, table=True):
    """一次分析任务。

    上传、解析、运行、复检都围绕这一行；进度与统计也写在这里。
    其余业务表都通过 analysis_id 级联关联，删除本行即删除整次分析。
    """

    __tablename__ = "analysis"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(max_length=255)  # 分析名称，默认取文件名
    status: str = Field(default="parsed", max_length=32)  # parsed/running/done/failed
    progress: int = Field(default=0)  # 0-100，供前端进度条
    stage: str | None = Field(default=None, max_length=64)  # 当前阶段名
    profile: str | None = Field(default=None, max_length=64)  # 选中的文档画像

    # 解析配置：抽取来源、字段映射、阈值等，重解析时复用
    config: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    # 本次运行使用的模型与提示词版本，用于复现与审计
    llm_enabled: bool = Field(default=False)
    model: str | None = Field(default=None, max_length=128)
    prompt_version: str | None = Field(default=None, max_length=32)
    embedding_model: str | None = Field(default=None, max_length=128)
    embedding_dim: int | None = Field(default=None)

    # 复检：指向被复检的上一次分析；被删除时置空
    previous_id: uuid.UUID | None = Field(
        default=None, foreign_key="analysis.id", ondelete="SET NULL"
    )

    stats: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)  # 覆盖率等指标
    diff: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)  # 新增/已闭环/仍存在
    error: str | None = Field(default=None)  # 失败原因
    created_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = Field(default=None)


class AnalysisDocument(SQLModel, table=True):
    """一次分析上传的源文档。

    正常恰好两条：role=requirements 与 role=design。
    保存磁盘路径、内容哈希、解析告警，便于回溯与去重。
    """

    __tablename__ = "document"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    analysis_id: uuid.UUID = Field(
        foreign_key="analysis.id", ondelete="CASCADE", index=True
    )
    role: str = Field(max_length=16)  # requirements 或 design
    filename: str = Field(max_length=512)  # 原始文件名
    stored_path: str = Field(max_length=1024)  # 服务器上的保存路径
    sha256: str = Field(max_length=64)  # 内容哈希，用于去重/校验
    size: int = Field(default=0)  # 文件字节数
    version_hint: str | None = Field(default=None, max_length=64)  # 从文件名/正文提取的版本
    warnings: list[str] = Field(default_factory=list, sa_type=JSON)  # 解析告警


class ParseDecision(SQLModel, table=True):
    """解析审计：每个候选块是否被判定为需求或设计要素。

    既记录被采纳的块，也记录被排除的块与理由，便于回答
    “这一段为什么没有进入分析”。
    """

    __tablename__ = "parse_decision"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    analysis_id: uuid.UUID = Field(
        foreign_key="analysis.id", ondelete="CASCADE", index=True
    )
    role: str = Field(max_length=16)  # requirements 或 design
    block_index: int = Field(default=0)  # 在文档中的块序号，用于定位
    section_no: str | None = Field(default=None, max_length=64)  # 来源章节号
    section_title: str | None = Field(default=None, max_length=512)  # 来源章节标题
    text: str  # 块原文（截断后）
    verdict: str = Field(max_length=32)  # requirement/group/not_requirement 或 element/not_element
    kind: str | None = Field(default=None, max_length=32)  # 需求类别或设计要素类型
    reason: str | None = Field(default=None, max_length=512)  # 判定理由
    confidence: float | None = Field(default=None)  # 判定置信度
    order_index: int = Field(default=0)  # 文档内顺序


class RequirementUnit(SQLModel, table=True):
    """需求单元：从需求文档抽出的可追溯容器。

    一个单元会被拆成若干原子需求（atomic_requirement），
    两者通过 atom_source 关联；父级综述单元标记 is_container，不单独计分。
    """

    __tablename__ = "requirement_unit"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    analysis_id: uuid.UUID = Field(
        foreign_key="analysis.id", ondelete="CASCADE", index=True
    )
    unit_key: str = Field(max_length=128)  # 分析内稳定的单元 key
    external_id: str | None = Field(default=None, max_length=128)  # 文档中的需求ID
    parent_external_id: str | None = Field(default=None, max_length=128)  # 父需求ID
    section_no: str | None = Field(default=None, max_length=64)  # 来源章节号
    section_title: str | None = Field(default=None, max_length=512)  # 来源章节标题
    title: str | None = Field(default=None, max_length=512)  # 单元标题
    description: str | None = Field(default=None)  # 需求描述/说明
    category: str | None = Field(default=None, max_length=32)  # 功能/性能/接口/数据等
    domain: str | None = Field(default=None, max_length=64)  # 平台或具体仪器域
    is_container: bool = Field(default=False)  # 父级综述，不参与单条计分
    judge_confidence: float | None = Field(default=None)  # 需求判定置信度
    judge_reason: str | None = Field(default=None, max_length=512)  # 需求判定理由
    order_index: int = Field(default=0)  # 文档内顺序
    raw_text: str = Field(default="")  # 原始文本，证据校验用


class AtomicRequirement(SQLModel, table=True):
    """原子需求：参与匹配的最小可验证断言。

    语义等价的原子会合并成一行，来源单元通过 atom_source 保留多条，
    因此“一个原子”可能同时属于多个需求单元。
    """

    __tablename__ = "atomic_requirement"

    # HNSW 索引属于数据库结构的一部分，写进 metadata，避免 autogenerate 误判为多余索引
    __table_args__ = (
        Index(
            "ix_atomic_requirement_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    analysis_id: uuid.UUID = Field(
        foreign_key="analysis.id", ondelete="CASCADE", index=True
    )
    text: str  # 原子断言原文
    search_text: str = Field(default="")  # 检索文本（原子 + 来源单元标题）
    kind: str = Field(max_length=32)  # 功能/界面/性能/接口/数据/安全/约束等
    has_metric: bool = Field(default=False)  # 是否含可比较的数值指标
    variant_count: int = Field(default=1)  # 合并了多少个变体
    merge_method: str | None = Field(default=None, max_length=32)  # exact/lexical/llm
    merge_confidence: float | None = Field(default=None)  # 合并置信度

    # 向量列：维度由 EMBEDDING_DIM 固定，用于 pgvector 相似检索
    embedding: list[float] | None = Field(
        default=None, sa_type=Vector(settings.EMBEDDING_DIM)
    )
    embedding_model: str | None = Field(default=None, max_length=128)  # 生成向量的模型
    text_hash: str | None = Field(default=None, max_length=64)  # 跳过未变文本的重复向量化
    order_index: int = Field(default=0)  # 分析内顺序


class AtomSource(SQLModel, table=True):
    """原子与需求单元的多对多连接。

    每个来源保留自己的原文片段（span_text），
    报告里展示证据时使用该单元自己的文字，而不是合并后的 canonical 文本。
    """

    __tablename__ = "atom_source"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    atom_id: uuid.UUID = Field(
        foreign_key="atomic_requirement.id", ondelete="CASCADE", index=True
    )
    unit_id: uuid.UUID = Field(
        foreign_key="requirement_unit.id", ondelete="CASCADE", index=True
    )
    seq: int = Field(default=0)  # 原子在该单元内的顺序
    span_text: str = Field(default="")  # 该单元中对应的原文片段


class DesignElement(SQLModel, table=True):
    """设计要素：从设计文档抽出的可匹配对象。

    kind 覆盖 module / submodule / interface / data_table / page /
    algorithm / constraint / nfr。字段按类型可空，证据校验只认原始字段值。
    """

    __tablename__ = "design_element"

    # 同上：向量列的 HNSW 索引登记到 metadata
    __table_args__ = (
        Index(
            "ix_design_element_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    analysis_id: uuid.UUID = Field(
        foreign_key="analysis.id", ondelete="CASCADE", index=True
    )
    element_key: str = Field(max_length=128)  # 分析内稳定的要素 key
    kind: str = Field(max_length=32)  # 要素类型
    code: str | None = Field(default=None, max_length=64)  # 文档中的模块编号
    name: str = Field(max_length=512)  # 要素名称
    level: str | None = Field(default=None, max_length=32)  # 系统级/子系统级/部件级
    domain: str | None = Field(default=None, max_length=64)  # 平台或具体仪器域
    section_no: str | None = Field(default=None, max_length=64)  # 来源章节号
    section_title: str | None = Field(default=None, max_length=512)  # 来源章节标题
    caption: str | None = Field(default=None, max_length=512)  # 表题

    # 模块设计表的字段
    description: str | None = Field(default=None)  # 功能描述
    interface: str | None = Field(default=None)  # 接口
    input: str | None = Field(default=None)  # 输入
    output: str | None = Field(default=None)  # 输出
    performance: str | None = Field(default=None)  # 性能
    constraints: str | None = Field(default=None)  # 限制条件
    test_points: str | None = Field(default=None)  # 测试要点
    narrative: str | None = Field(default=None)  # 同章节相邻叙述

    attributes: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)  # 页面动作/导航等
    fields: list[dict[str, Any]] = Field(default_factory=list, sa_type=JSON)  # 数据表字段
    search_text: str = Field(default="")  # BM25F 与向量共用的检索文本
    raw_text: str = Field(default="")  # 原始文本，证据校验用

    embedding: list[float] | None = Field(
        default=None, sa_type=Vector(settings.EMBEDDING_DIM)
    )
    embedding_model: str | None = Field(default=None, max_length=128)
    text_hash: str | None = Field(default=None, max_length=64)

    variants: list[dict[str, Any]] = Field(default_factory=list, sa_type=JSON)  # 同体合并保留的变体
    source_refs: list[dict[str, Any]] = Field(default_factory=list, sa_type=JSON)  # 段落/表格定位
    parent_code: str | None = Field(default=None, max_length=64)  # 子模块的父模块编号
    order_index: int = Field(default=0)  # 分析内顺序


class AtomMapping(SQLModel, table=True):
    """原子与设计要素的判定结果。

    relation 取 satisfy / partial / contradict / uncertain；
    未覆盖不落成一行，而是“这个原子没有任何 satisfy/partial 边”。
    人工复核可接受或推翻自动判定。
    """

    __tablename__ = "mapping"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    analysis_id: uuid.UUID = Field(
        foreign_key="analysis.id", ondelete="CASCADE", index=True
    )
    atom_id: uuid.UUID = Field(
        foreign_key="atomic_requirement.id", ondelete="CASCADE", index=True
    )
    element_id: uuid.UUID = Field(
        foreign_key="design_element.id", ondelete="CASCADE", index=True
    )
    relation: str = Field(max_length=16)  # satisfy/partial/contradict/uncertain
    confidence: float = Field(default=0.0)  # 判定置信度
    method: str = Field(default="llm", max_length=16)  # rule/lexical/llm/manual
    rationale: str | None = Field(default=None)  # 判定理由
    evidence: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)  # {atom, element} 原文片段
    review_status: str = Field(default="open", max_length=16)  # open/accepted/rejected
    review_note: str | None = Field(default=None)  # 人工复核备注
    created_at: datetime = Field(default_factory=utcnow)


class Finding(SQLModel, table=True):
    """问题清单：由确定性规则或语义判定产生。

    unit_refs / atom_refs / element_refs 存外部编号或分析内 key 的数组，
    不设外键，避免单条引用记录被删除后问题随之消失。
    fingerprint 用于复检时判断“新增 / 已闭环 / 仍存在”。
    """

    __tablename__ = "finding"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    analysis_id: uuid.UUID = Field(
        foreign_key="analysis.id", ondelete="CASCADE", index=True
    )
    code: str = Field(max_length=64)  # 问题编码，如 SEM-UNCOVERED、RQ-PARENT-SELF
    dimension: str = Field(max_length=32)  # 追踪/完整/语义/接口数据/性能/规范/内部
    severity: str = Field(max_length=16)  # blocker/major/minor/info
    title: str = Field(max_length=512)  # 问题标题
    detail: str = Field(default="")  # 问题详情
    unit_refs: list[str] = Field(default_factory=list, sa_type=JSON)  # 关联需求单元
    atom_refs: list[str] = Field(default_factory=list, sa_type=JSON)  # 关联原子
    element_refs: list[str] = Field(default_factory=list, sa_type=JSON)  # 关联设计要素
    evidence: list[dict[str, Any]] = Field(default_factory=list, sa_type=JSON)  # 证据列表
    suggestion: str | None = Field(default=None)  # 修改建议
    confidence: float | None = Field(default=None)  # 语义问题的置信度
    source: str = Field(default="rule", max_length=16)  # rule 或 llm
    fingerprint: str = Field(default="", max_length=128, index=True)  # 复检比对用
    status: str = Field(default="open", max_length=16)  # open/confirmed/fixed/ignored
    note: str | None = Field(default=None)  # 处理备注
    updated_at: datetime = Field(default_factory=utcnow)


class LlmCache(SQLModel, table=True):
    """模型响应缓存。

    key = sha256(model + prompt_version + 输入负载)，
    相同输入重跑时直接命中，避免重复计费。
    """

    __tablename__ = "llm_cache"

    key: str = Field(primary_key=True, max_length=128)  # 缓存键
    model: str = Field(max_length=128)  # 生成响应的模型
    prompt_version: str = Field(max_length=32)  # 提示词版本
    response: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)  # 原始响应
    created_at: datetime = Field(default_factory=utcnow)
