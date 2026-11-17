from __future__ import annotations

from typing import Optional

from src.config import Settings
from src.rag.classify import Intent
from src.schemes import SCHEMES

_CAN_ANSWER = (
    "I can share verified facts such as expense ratio, exit load, SIP minimums, "
    "lock-in, NAV, or riskometer for the supported HDFC schemes."
)


def _groww_url(scheme_id: Optional[str]) -> Optional[str]:
    if not scheme_id:
        return None
    meta = SCHEMES.get(scheme_id)
    if not meta:
        return None
    return str(meta["groww_url"])


def build_refusal(
    intent: Intent, scheme_id: Optional[str], settings: Settings
) -> str:
    if intent is Intent.ADVISORY:
        return (
            "I can't provide investment advice or fund recommendations. "
            f"{_CAN_ANSWER} "
            f"For investor education, see: {settings.educational_link}"
        )

    if intent is Intent.COMPARATIVE:
        return (
            "I can't compare funds or say which is better. "
            f"{_CAN_ANSWER} "
            f"For investor education, see: {settings.educational_link}"
        )

    if intent is Intent.PERFORMANCE:
        url = _groww_url(scheme_id)
        if url:
            return (
                "I don't calculate or quote historical returns. "
                f"Please check the scheme page on Groww for performance data: {url}"
            )
        return (
            "I don't calculate or quote historical returns. "
            "Please open the relevant scheme page on Groww for performance data. "
            f"{_CAN_ANSWER}"
        )

    if intent is Intent.PII_SENSITIVE:
        return (
            "I can't process personal or account identifiers, and I won't store them. "
            "Please ask a factual question about a supported HDFC scheme "
            "(for example expense ratio or exit load) without sharing personal details."
        )

    if intent is Intent.OUT_OF_CORPUS:
        return (
            "That looks outside this assistant's corpus. "
            "I only cover five HDFC Direct Growth schemes on Groww "
            "(mid-cap, small-cap, gold FoF, large-cap, and ELSS tax saver). "
            f"{_CAN_ANSWER}"
        )

    if intent is Intent.UNCLEAR:
        return (
            "I'm not sure which factual scheme detail you need. "
            "Please ask about a supported HDFC scheme fact "
            "(expense ratio, exit load, SIP minimum, lock-in, NAV, and similar)."
        )

    # FACTUAL_* reaching refuse path (e.g. empty retrieval) — soft out-of-corpus.
    return (
        "I couldn't find that fact in the indexed Groww scheme pages. "
        f"{_CAN_ANSWER}"
    )
