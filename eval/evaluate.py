"""How good are MCP_Agentic_DocuChat's answers? This script finds out.

It asks 4 fixed questions (summary, methods, limitations, plus a trap
question no PDF can answer), then scores each reply 0–1 on faithfulness
(backed by the paper?), relevancy (actually answers you?), and whether
the right pages were pulled.

With GEMINI_API_KEY set, DeepEval's judge model does the scoring.
Without keys it still runs — simple offline checks (page cited? honest
"not in the paper"?) so CI stays green anywhere.

Run:  python eval/evaluate.py --document ./data/research_paper.pdf
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

GOLDEN_SET = [
    {
        "question": "What are the main findings of the document?",
        "expected": "A summary grounded in the PDF with page citations.",
    },
    {
        "question": "What methodology does the paper use?",
        "expected": "The method/architecture described in the PDF, cited by page.",
    },
    {
        "question": "What are the limitations or future work mentioned?",
        "expected": "Limitations stated in the PDF, or an honest 'not found'.",
    },
    {
        "question": "Who is the president of Mars?",
        "expected": "The document does not contain enough information to answer this.",
    },
]


def _local_scores(answer: str, sources: list) -> dict:
    """Offline fallback metrics when no judge LLM is available."""
    text = answer.lower()
    has_citation = "page" in text
    admits_gap = "does not contain enough" in text
    grounded = has_citation or admits_gap or len(sources) > 0
    return {
        "faithfulness": 1.0 if grounded else 0.0,
        "answer_relevancy": 0.0 if len(answer.strip()) < 20 else 0.8,
        "context_precision": 1.0 if sources else 0.0,
    }


async def _run_case(backend, case: dict, provider: str, user_id: str = "eval") -> dict:
    result = await backend.ask(case["question"], user_id=user_id, provider=provider)
    answer = result.get("answer", "")
    sources = result.get("sources", [])

    judge_key = os.getenv("GEMINI_API_KEY")
    if judge_key:
        try:
            from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
            from deepeval.test_case import LLMTestCase

            test_case = LLMTestCase(
                input=case["question"],
                actual_output=answer,
                expected_output=case["expected"],
                retrieval_context=[str(s) for s in sources] or [answer],
            )
            faith = FaithfulnessMetric(model="gemini-3.5-flash-lite")
            rel = AnswerRelevancyMetric(model="gemini-3.5-flash-lite")
            await faith.a_measure(test_case)
            await rel.a_measure(test_case)
            return {
                "question": case["question"],
                "answer": answer[:500],
                "faithfulness": round(float(faith.score or 0), 3),
                "answer_relevancy": round(float(rel.score or 0), 3),
                "context_precision": 1.0 if sources else 0.0,
                "judge": "deepeval/gemini",
            }
        except Exception as error:  # fall through to offline scores
            print(f"DeepEval judge failed ({error}); using offline checks.")

    return {
        "question": case["question"],
        "answer": answer[:500],
        "judge": "offline",
        **_local_scores(answer, sources),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate MCP_Agentic_DocuChat RAG quality")
    parser.add_argument("--document", default=os.getenv("DOCUMENT_PATH", "./data/research_paper.pdf"))
    parser.add_argument("--provider", default="llamacpp", choices=["gemini", "ollama", "llamacpp"])
    args = parser.parse_args()

    from agentic_docuchat.rag.backend import RagBackend

    try:
        backend = RagBackend(document_path=args.document)
    except Exception as error:
        print(f"Backend not ready ({error}). Running answer-shape checks only.")
        backend = None

    rows = []
    if backend is None:
        for case in GOLDEN_SET:
            rows.append({"question": case["question"], "answer": "", "judge": "skipped",
                         "faithfulness": 0.0, "answer_relevancy": 0.0, "context_precision": 0.0})
    else:
        # A distinct user per case: the backend's per-user rate limit would
        # otherwise fail every question after the first with a cooldown error.
        for index, case in enumerate(GOLDEN_SET):
            try:
                rows.append(await _run_case(backend, case, args.provider, user_id=f"eval-{index}"))
            except Exception as error:
                rows.append({"question": case["question"], "answer": f"ERROR: {error}",
                             "judge": "error", "faithfulness": 0.0,
                             "answer_relevancy": 0.0, "context_precision": 0.0})

    print(f"\n{'Question':<55} {'Faith':>6} {'Relev':>6} {'CtxPrec':>8}  Judge")
    print("-" * 100)
    for row in rows:
        print(f"{row['question'][:54]:<55} {row['faithfulness']:>6.2f} "
              f"{row['answer_relevancy']:>6.2f} {row['context_precision']:>8.2f}  {row['judge']}")
    avg_f = sum(r["faithfulness"] for r in rows) / max(len(rows), 1)
    print("-" * 100)
    print(f"Average faithfulness: {avg_f:.2f}  (aim for 0.80+ before sharing)")


if __name__ == "__main__":
    asyncio.run(main())
