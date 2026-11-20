from __future__ import annotations

from typing import Tuple

from src.desk import draft_agent, policy_agent, retrieve_agent
from src.desk.faq_client import RetrieveResult
from src.desk.policy_agent import PolicyResult


def run_agents_parallel(
    question: str,
    *,
    fixture_mode: bool | None = None,
) -> Tuple[PolicyResult, RetrieveResult, str]:
    """Run policy → retrieve → draft.

    Sequential on purpose: Support Deck and FAQ both use a top-level ``src``
    package. Parallel retrieve swaps ``sys.modules['src']`` for the FAQ tree and
    races other agents when embedded on the Railway FAQ process (500s in prod).
    """
    policy = policy_agent.run_policy(question)
    retrieve = retrieve_agent.run_retrieve(question)
    draft = draft_agent.run_draft(question, retrieve, fixture_mode=fixture_mode)
    return policy, retrieve, draft
