from datetime import datetime

from src.desk.faq_client import RetrieveResult
from src.desk.orchestrator import CandidateReply
from src.desk.policy_agent import PolicyResult
from src.desk.reviewer import ReviewResult
from src.models import FrequencyBucket, QueueStatus


def _retrieve():
    return RetrieveResult(
        chunks=[
            {
                "text": "Exit load 1%",
                "source_url": "https://groww.in/p/exit-load",
            }
        ],
        source_urls=["https://groww.in/p/exit-load"],
        searched=["FAQ corpus", "https://groww.in/p/exit-load"],
    )


def test_build_faq_path_package():
    from src.desk.agent_package import build_agent_package

    policy = PolicyResult(allow=True, refuse=False, reasons=["ok"], category="factual")
    candidate = CandidateReply(
        status=QueueStatus.drafted,
        draft="Exit load is 1%. https://groww.in/p/exit-load",
        citation_url="https://groww.in/p/exit-load",
        routing_note="answer",
        searched=["FAQ corpus"],
    )
    reviewed = ReviewResult(candidate=candidate, flags=[], passed=True)
    bucket = FrequencyBucket(
        bucket_id="fb-x",
        normalized_text="exit load",
        count=1,
        window_start=datetime(2026, 1, 1),
        window_end=datetime(2026, 1, 2),
    )
    pkg = build_agent_package(
        retrieve=_retrieve(),
        policy=policy,
        reviewed=reviewed,
        bucket=bucket,
        retrieve_path="faq",
        agents_fired_base=["retrieve", "draft", "policy", "orchestrator", "reviewer"],
        frequency_threshold=5,
        window_days=7,
    )
    assert pkg["retrieve"]["path"] == "faq"
    assert pkg["retrieve"]["chunk_count"] == 1
    assert pkg["policy"]["refuse"] is False
    assert pkg["pattern"]["count"] == 1
    assert pkg["pattern"]["recurring"] is False
    assert pkg["reviewer"]["passed"] is True
    assert pkg["reviewer"]["round"] == 1
    assert pkg["agents_fired"][-1] == "pattern"
    assert "draft" in pkg["agents_fired"]


def test_build_explainer_reuse_omits_draft_agent():
    from src.desk.agent_package import build_agent_package

    policy = PolicyResult(allow=True, refuse=False, reasons=[], category="factual")
    candidate = CandidateReply(
        status=QueueStatus.drafted,
        draft="Fees explained.",
        citation_url="https://a.example/1",
        routing_note="reuse_explainer",
        searched=["fee_explainer"],
    )
    reviewed = ReviewResult(candidate=candidate, flags=[], passed=True)
    bucket = FrequencyBucket(
        bucket_id="fb-y", normalized_text="fees", count=6
    )
    pkg = build_agent_package(
        retrieve=RetrieveResult(chunks=[], source_urls=[], searched=["fee_explainer"]),
        policy=policy,
        reviewed=reviewed,
        bucket=bucket,
        retrieve_path="reuse_explainer",
        agents_fired_base=["policy", "retrieve", "orchestrator", "reviewer"],
        frequency_threshold=5,
        window_days=7,
    )
    assert "draft" not in pkg["agents_fired"]
    assert pkg["draft"]["text"]
    assert pkg["pattern"]["recurring"] is True
    assert pkg["retrieve"]["path"] == "reuse_explainer"


def test_build_policy_refuse_package():
    from src.desk.agent_package import build_agent_package

    policy = PolicyResult(allow=False, refuse=True, reasons=["pii"], category="pii")
    candidate = CandidateReply(
        status=QueueStatus.not_covered,
        draft="not_covered: personal data.",
        citation_url=None,
        routing_note="escalate_human",
        searched=["FAQ corpus"],
    )
    reviewed = ReviewResult(candidate=candidate, flags=["pii"], passed=False)
    bucket = FrequencyBucket(bucket_id="fb-z", normalized_text="pan", count=1)
    pkg = build_agent_package(
        retrieve=_retrieve(),
        policy=policy,
        reviewed=reviewed,
        bucket=bucket,
        retrieve_path="faq",
        agents_fired_base=["retrieve", "draft", "policy", "orchestrator", "reviewer"],
        frequency_threshold=5,
        window_days=7,
    )
    assert pkg["policy"]["refuse"] is True
    assert pkg["policy"]["category"] == "pii"
    assert pkg["orchestrator"]["routing_note"] == "escalate_human"
    assert pkg["reviewer"]["passed"] is False
