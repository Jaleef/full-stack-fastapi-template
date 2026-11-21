"""设计文档抽取：块判定、字段抽取、关联合并与去重。"""

from __future__ import annotations

from pydantic import BaseModel

from app.domain import Block, DesignKind
from app.models import DesignElement
from app.services.llm import LLMClient
from app.services.parsing import Profile


class DesignDecision(BaseModel):
    """一个候选块的设计要素判定结果。"""

    index: int
    verdict: str
    kind: str | None = None
    reason: str | None = None
    confidence: float | None = None


def rule_kind(block: Block) -> DesignKind | None:
    """结构特征明显时直接返回要素类型。"""
    ...


def judge_blocks(client: LLMClient, blocks: list[Block]) -> list[DesignDecision]:
    """用模型判定结构特征不明显的块。"""
    ...


def extract_module(
    block: Block,
    labels: list[str],
    profile: Profile,
) -> DesignElement:
    """从模块设计表抽取一个模块要素。"""
    ...


def extract_data_table(block: Block) -> DesignElement:
    """抽取数据库表要素及其字段定义。"""
    ...


def extract_page(block: Block, section_title: str) -> DesignElement:
    """从页面设计小节抽取页面要素。"""
    ...


def extract_constraint(block: Block) -> list[DesignElement]:
    """把技术选型或环境约束表按行拆成要素。"""
    ...


def extract_interface(block: Block) -> DesignElement:
    """抽取模块表之外定义的接口要素。"""
    ...


def extract_nfr(block: Block, client: LLMClient) -> DesignElement:
    """抽取性能、安全或可靠性设计要素。"""
    ...


def extract_section_element(block: Block, section_title: str) -> DesignElement:
    """在没有表格的章节按正文生成要素。"""
    ...


def attach_narrative(element: DesignElement, neighbors: list[str]) -> DesignElement:
    """把相邻叙述段落合并进要素的检索文本。"""
    ...


def infer_level(text: str) -> str:
    """从措辞判断系统级、子系统级或部件级。"""
    ...


def infer_domain(section_title: str) -> str:
    """从章节标题判断平台或具体仪器域。"""
    ...


def attach_endpoints(element: DesignElement) -> DesignElement:
    """从接口字段解析出 API 端点。"""
    ...


def same_element_candidates(
    elements: list[DesignElement],
    k: int = 5,
) -> list[tuple[int, int, float]]:
    """召回可能描述同一设计对象的要素对。"""
    ...


def confirm_same(
    client: LLMClient,
    elements: list[DesignElement],
    pairs: list[tuple[int, int, float]],
) -> list[bool]:
    """让模型确认每一对要素是否同一设计对象。"""
    ...


def merge_elements(
    elements: list[DesignElement],
    pairs: list[tuple[int, int, float]],
) -> list[DesignElement]:
    """合并确认相同的要素，并保留来源并集。"""
    ...


def build_element_search_text(element: DesignElement) -> str:
    """把要素字段渲染成带标签的检索文本。"""
    ...


def build_atom_search_text(unit_title: str, atom_text: str) -> str:
    """拼装原子需求的检索文本，附带来源单元标题。"""
    ...
