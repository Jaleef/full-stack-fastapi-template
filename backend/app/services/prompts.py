"""提示词构建。"""

from __future__ import annotations

from typing import Any

PROMPT_VERSION = "v1"


def build_requirement_judge_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    """构建“候选块是否为真实需求”的提示词。"""
    ...


def build_atomize_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    """构建“把需求单元拆成原子断言”的提示词。"""
    ...


def build_equivalence_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    """构建“两条原子是否语义等价”的提示词。"""
    ...


def build_design_judge_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    """构建“候选块是否为设计要素”的提示词。"""
    ...


def build_design_extract_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    """构建“从正文抽取设计要素字段”的提示词。"""
    ...


def build_mapping_judge_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    """构建“原子需求对候选要素裁决”的提示词。"""
    ...


def build_reverse_judge_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    """构建“无入边要素是否有需求依据”的提示词。"""
    ...
