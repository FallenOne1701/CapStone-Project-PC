from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Tuple

from src.desk import draft_agent, policy_agent, retrieve_agent
from src.desk.faq_client import RetrieveResult
from src.desk.policy_agent import PolicyResult


def run_agents_parallel(
    question: str,
    *,
    fixture_mode: bool | None = None,
) -> Tuple[PolicyResult, RetrieveResult, str]:
    """Run policy + retrieve concurrently, then draft from retrieve (still overlapping policy).

    Draft depends on retrieve context, so pure triple-gather is not possible without
    duplicating retrieve. Policy always overlaps retrieve and draft.
    """
    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_policy = pool.submit(policy_agent.run_policy, question)
        fut_retrieve = pool.submit(retrieve_agent.run_retrieve, question)
        retrieve = fut_retrieve.result()
        fut_draft = pool.submit(
            draft_agent.run_draft, question, retrieve, fixture_mode=fixture_mode
        )
        policy = fut_policy.result()
        draft = fut_draft.result()
    return policy, retrieve, draft
