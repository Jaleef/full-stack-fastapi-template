"""打印两份样例文档的块与候选统计，用于 B8 阶段自测。"""

from __future__ import annotations

import logging
import sys
from collections import Counter

from app.core.config import settings
from app.domain import DocRole
from app.services.docx_reader import iter_blocks
from app.services.parsing import Profile, iter_headings, parse_toc, split_blocks

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
logger = logging.getLogger("inspect_blocks")

CASES = (
    ("requirements.docx", DocRole.REQUIREMENTS),
    ("design.docx", DocRole.DESIGN),
)


def _reason_groups(candidates) -> dict[str, int]:
    """把切块原因按大类聚合，便于打印。"""
    groups: Counter[str] = Counter()
    for candidate in candidates:
        reason = candidate.reason or ""
        if reason.startswith("table:chunk"):
            groups["table:chunk"] += 1
        elif reason.startswith("table:constraint"):
            groups["table:constraint"] += 1
        else:
            groups[reason] += 1
    return dict(groups)


def main() -> int:
    """逐份样例打印块类型、标题与候选统计。"""
    missing = [name for name, _role in CASES if not (settings.SAMPLE_DIR / name).exists()]
    if missing:
        logger.error(
            "样例文档不存在：%s（请放到 %s）",
            ", ".join(missing),
            settings.SAMPLE_DIR,
        )
        return 1

    for name, role in CASES:
        path = settings.SAMPLE_DIR / name
        blocks = list(iter_blocks(path))
        headings = list(iter_headings(blocks))
        toc = parse_toc(blocks)
        candidates = split_blocks(blocks, role, Profile(name="generic"))
        block_kinds = Counter(block.kind.value for block in blocks)
        max_text = max((len(candidate.block.text) for candidate in candidates), default=0)
        truncated = sum(
            1
            for candidate in candidates
            if candidate.block.text.endswith("…（已截断）")
        )

        logger.info("%s", name)
        logger.info("  blocks=%d kinds=%s", len(blocks), dict(block_kinds))
        logger.info("  headings=%d toc=%d", len(headings), len(toc))
        logger.info(
            "  candidates=%d reasons=%s",
            len(candidates),
            _reason_groups(candidates),
        )
        logger.info("  max_text=%d truncated=%d", max_text, truncated)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
