"""领域枚举与轻量数据结构。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class DocRole(StrEnum):
    """文档角色：需求文档或设计文档。"""

    REQUIREMENTS = "requirements"
    DESIGN = "design"


class BlockKind(StrEnum):
    """文档块类型。"""

    HEADING = "heading"         # 标题块
    PARAGRAPH = "paragraph"     # 普通段落块
    TABLE = "table"             # 表格块
    CAPTION = "caption"         # 图表说明块
    FORMULA = "formula"         # 公式块
    IMAGE = "image"             # 图片块


class AnalysisStatus(StrEnum):
    """分析任务状态。"""

    PARSED = "parsed"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class DesignKind(StrEnum):
    """设计要素类型。"""

    MODULE = "module"
    SUBMODULE = "submodule"
    INTERFACE = "interface"
    DATA_TABLE = "data_table"
    PAGE = "page"
    ALGORITHM = "algorithm"
    CONSTRAINT = "constraint"
    NFR = "nfr"


class Relation(StrEnum):
    """原子需求与设计要素之间的关系。"""

    SATISFY = "satisfy"
    PARTIAL = "partial"
    CONTRADICT = "contradict"
    UNCERTAIN = "uncertain"


class Severity(StrEnum):
    """问题严重程度。"""

    BLOCKER = "blocker"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class Dimension(StrEnum):
    """一致性维度。"""

    TRACEABILITY = "traceability"
    COMPLETENESS = "completeness"
    SEMANTIC = "semantic"
    INTERFACE_DATA = "interface_data"
    PERFORMANCE = "performance"
    STRUCTURAL = "structural"
    INTERNAL = "internal"


class FindingStatus(StrEnum):
    """问题处理状态。"""

    OPEN = "open"
    CONFIRMED = "confirmed"
    FIXED = "fixed"
    IGNORED = "ignored"


class ReviewStatus(StrEnum):
    """映射人工复核状态。"""

    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ElementSource(StrEnum):
    """设计要素的抽取来源。"""

    TABLE = "table"
    SECTION = "section"
    LLM = "llm"


@dataclass(slots=True)
class Block:
    """按文档顺序读取的一个结构块。"""

    kind: BlockKind
    text: str
    index: int
    table: list[list[str]] | None = None
    caption: str | None = None


@dataclass(slots=True)
class Heading:
    """解析后的标题及其层级。"""

    number: str
    title: str
    level: int


@dataclass(slots=True)
class Section:
    """块所属的章节。"""

    number: str = ""
    title: str = ""
    level: int = 0
    path: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CandidateBlock:
    """待判定的需求或设计候选块。"""

    block: Block
    section: Section
    role: DocRole
    reason: str | None = None
    context: str = ""


@dataclass(slots=True)
class Evidence:
    """支撑一次判定的双侧原文片段。"""

    atom_quote: str = ""
    element_quote: str = ""


@dataclass(slots=True)
class Candidate:
    """为一个原子需求召回到的设计要素候选。"""

    element_id: uuid.UUID
    element_key: str
    score: float
    sources: list[str] = field(default_factory=list)
    kind: str = ""
