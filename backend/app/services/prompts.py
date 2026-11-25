"""提示词构建。"""

from __future__ import annotations

import json
from typing import Any

PROMPT_VERSION = "v2"

REQUIREMENT_VERDICTS = ("requirement", "group", "not_requirement")
REQUIREMENT_KINDS = (
    "functional",
    "performance",
    "interface",
    "data",
    "security",
    "constraint",
    "ui",
    "other",
)


def build_requirement_judge_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    """构建“候选块是否为真实需求”的提示词。"""
    system = """你是软件需求一致性分析系统的需求审查员。
你的判断必须适用于任意行业、任意模板的软件需求规格说明，不要依赖章节编号、固定前缀或某种特定文档标准。

你的任务是判断每个候选块是否承载一条可验证的软件需求。

判定标签：
- requirement：描述系统或软件应具备的行为、能力、输入输出、接口、数据、性能、安全、界面或约束，且可以被验证。
- group：章节导语、分组标题或范围说明，概括多条需求，但自身不是一条可独立验证的断言。
- not_requirement：目录、修订记录、封面、审批页、图题、表题、模板说明、纯背景、术语定义、读者说明等。

判定原则：
1. 只看块本身的文本，不要根据章节编号、字体或文档模板猜测。
2. 一条块里包含多条独立断言时，仍然判 requirement，拆分留给后续原子化阶段。
3. 表格行按行内容判断；表头和表题本身不是需求。
4. 描述实现方案、技术选型或背景信息，而不是系统应满足的要求时，倾向 not_requirement 或 group。
5. 中英文均可，不要因为语言、行业术语或编号风格不同而拒判。
6. reason 用简洁的一句话说明判断依据。

kind 只能取以下值之一（不适用时用 null）：
functional, performance, interface, data, security, constraint, ui, other

只输出严格 JSON，不要 Markdown，不要前后解释：
{"decisions":[{"index":0,"verdict":"requirement","kind":"functional","reason":"不超过50字","confidence":0.9}]}

硬性要求：
1. 每个输入 index 必须且只能出现一次；
2. verdict 只能是 requirement / group / not_requirement；
3. kind 只能是上述八类之一或 null；
4. confidence 是 0 到 1 之间的小数；
5. 不要输出 JSON 之外的任何文字。"""

    user = "候选块（JSON）：\n" + json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


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
