from prometheus_client import Counter, Gauge, Histogram

# ── Request metrics ───────────────────────────────────────────────────────────

rag_requests_total = Counter(
    "rag_request_total",
    "Total RAG requests",
    ["endpoint", "status"],
)

rag_latency_seconds = Histogram(
    "rag_latency_seconds",
    "End-to-end RAG request latency",
    ["endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# ── Retrieval metrics ─────────────────────────────────────────────────────────

retrieval_latency_seconds = Histogram(
    "retrieval_latency_seconds",
    "Vector retrieval latency",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0],
)

retrieval_precision_at_k = Gauge(
    "retrieval_precision_at_k",
    "Rolling retrieval precision@k from eval",
)

# ── LLM metrics ───────────────────────────────────────────────────────────────

llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "LLM completion latency",
    ["model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 15.0, 30.0],
)

tokens_total = Counter(
    "tokens_total",
    "Total tokens consumed",
    ["model", "token_type"],  # token_type: prompt | completion
)

estimated_cost_usd_total = Counter(
    "estimated_cost_usd_total",
    "Estimated LLM cost in USD",
    ["model"],
)

# ── Quality metrics ───────────────────────────────────────────────────────────

groundedness_score = Gauge(
    "groundedness_score",
    "Rolling groundedness score from eval",
)

hallucination_rate = Gauge(
    "hallucination_rate",
    "Rolling fraction of ungrounded answers",
)

# ── Agent metrics ─────────────────────────────────────────────────────────────

agent_tool_calls_total = Counter(
    "agent_tool_calls_total",
    "Total agent tool invocations",
    ["tool_name"],
)
