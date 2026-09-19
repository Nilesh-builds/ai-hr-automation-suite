"""HR policy Q&A with grounded answers.

The rule-based baseline retrieves the most relevant policy via keyword
scoring and returns an excerpt verbatim, guaranteeing a grounded answer.
The LLM path answers from the retrieved context and is rewarded only when
it stays grounded in the policy corpus.
"""

from __future__ import annotations

from .. import config
from ..models import Policy


def _tokenize(text: str) -> set[str]:
    words = set(text.lower().split())
    words.discard("")
    return words


STOP_WORDS = {
    "what", "is", "the", "how", "many", "days", "our", "policy", "on",
    "for", "of", "to", "a", "an", "i", "we", "my", "do", "can",
    "do", "are", "during", "each", "get", "will", "when", "need",
}


def _search_tokens(text: str) -> set[str]:
    tokens = _tokenize(text)
    stems = {t[:-1] for t in tokens if len(t) > 3 and t.endswith("s")}
    return tokens | stems


def retrieve_policies(question: str, policies: list[Policy], top_k: int = 3) -> list[Policy]:
    q_tokens = _search_tokens(question) - STOP_WORDS
    scored = []
    for policy in policies:
        title_tokens = _search_tokens(policy.title) - STOP_WORDS
        body_tokens = _search_tokens(policy.body) - STOP_WORDS
        title_overlap = len(q_tokens & title_tokens)
        body_overlap = len(q_tokens & body_tokens)
        score = title_overlap + body_overlap
        if score:
            scored.append((score, policy))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [policy for _, policy in scored[:top_k]]


def answer_policy_rule_based(question: str, policies: list[Policy]) -> dict:
    hits = retrieve_policies(question, policies)
    if not hits:
        return {
            "answer": "I could not find a matching policy. Please contact HR.",
            "policy_ids": [],
            "grounded": False,
            "confidence": 0.0,
        }

    best = hits[0]
    excerpt = best.body.replace("\n", " ").strip()[:300]
    return {
        "answer": excerpt,
        "policy_ids": [best.policy_id],
        "grounded": True,
        "confidence": 0.9,
    }


_LLM_SYSTEM = (
    "You are an HR policy assistant. Answer ONLY from the provided policy "
    "context. If the answer is not in the context, say you are unsure and "
    "refer the employee to HR. Be concise. Return JSON only: "
    "{\"answer\":string,\"policyIds\":[string],\"grounded\":bool}."
)


def answer_policy_llm(question: str, policies: list[Policy]) -> dict:
    from openai import OpenAI

    context = "\n\n".join(
        f"[{p.policy_id}] {p.title}\n{p.body}" for p in policies
    )
    client = OpenAI(api_key=config.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=config.llm_model(),
        temperature=0.0,
        messages=[
            {"role": "system", "content": _LLM_SYSTEM},
            {"role": "user", "content": f"Policy context:\n{context}\n\nQuestion: {question}"},
        ],
    )
    raw = response.choices[0].message.content or ""
    # groundedness is the model's own assertion; enforce it against retrieved ids
    try:
        payload = config.extract_json(raw)
        answer = str(payload.get("answer", ""))
        policy_ids = [str(p) for p in (payload.get("policyIds") or [])]
        grounded = bool(payload.get("grounded", False))
    except (ValueError, TypeError):
        return {
            "answer": "I could not answer this reliably. Please contact HR.",
            "policy_ids": [],
            "grounded": False,
            "confidence": 0.5,
        }
    # We can only be grounded if the cited id is actually in our policy corpus.
    valid_ids = {p.policy_id for p in policies}
    grounded = grounded and bool(valid_ids & set(policy_ids))
    return {
        "answer": answer,
        "policy_ids": policy_ids,
        "grounded": grounded,
        "confidence": 0.9 if grounded else 0.6,
    }


def answer_policy(question: str, policies: list[Policy]) -> dict:
    if config.llm_available():
        return answer_policy_llm(question, policies)
    return answer_policy_rule_based(question, policies)