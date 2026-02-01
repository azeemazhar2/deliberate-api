# Deliberate API

Multi-agent deliberation service that stress-tests ideas through structured AI debate.

## Live API

**Base URL**: `https://deliberate-api.fly.dev`

**API Key**: `xyz-123-154`

## How It Works

1. **R1 (Independent Analysis)**: 3 AI agents independently analyze your thesis
2. **R2 (Cross-Reading)**: Each agent reviews the others' analyses (anonymized)
3. **R3 (Synthesis)**: Produces a verdict with agreements and divergences

## API Endpoints

### Health Check

```bash
curl https://deliberate-api.fly.dev/health
```

### Start a Deliberation

```bash
curl -X POST https://deliberate-api.fly.dev/v1/deliberate \
  -H "X-API-Key: xyz-123-154" \
  -H "Content-Type: application/json" \
  -d '{
    "thesis": "Cats are softer than dogs",
    "context": "Optional additional context here"
  }'
```

Response:
```json
{
  "job_id": "dlb_abc123",
  "status": "pending",
  "poll_url": "/v1/jobs/dlb_abc123"
}
```

### Poll for Results

```bash
curl https://deliberate-api.fly.dev/v1/jobs/dlb_abc123 \
  -H "X-API-Key: xyz-123-154"
```

Status progression: `pending` → `running` → `completed`

Response (when complete):
```json
{
  "job_id": "dlb_abc123",
  "status": "completed",
  "current_round": 3,
  "result": {
    "verdict": "Summary of the deliberation outcome",
    "confidence": "high|medium|low",
    "reasoning": "Explanation of how the verdict was reached",
    "key_agreements": [
      "Point all agents agreed on",
      "Another agreement"
    ],
    "divergences": [
      {
        "topic": "Topic of disagreement",
        "description": "What they disagreed about",
        "positions": [
          {"view": "Agent 1's position", "confidence": "high"},
          {"view": "Agent 2's position", "confidence": "medium"},
          {"view": "Agent 3's position", "confidence": "low"}
        ]
      }
    ],
    "tokens_used": 19000,
    "rounds_completed": 3
  },
  "created_at": "2026-02-01T21:41:21.612808",
  "completed_at": "2026-02-01T21:42:12.170691"
}
```

### List Recent Jobs

```bash
curl https://deliberate-api.fly.dev/v1/jobs \
  -H "X-API-Key: xyz-123-154"
```

## Custom Models

Override the default models by specifying exactly 3 models:

```bash
curl -X POST https://deliberate-api.fly.dev/v1/deliberate \
  -H "X-API-Key: xyz-123-154" \
  -H "Content-Type: application/json" \
  -d '{
    "thesis": "Your thesis here",
    "models": [
      "anthropic/claude-sonnet-4-20250514",
      "openai/gpt-4o",
      "google/gemini-2.0-flash-001"
    ]
  }'
```

Default models:
- `anthropic/claude-haiku-4.5`
- `liquid/lfm-2.5-1.2b-thinking:free`
- `google/gemini-3-flash-preview`

## Interactive Docs

Swagger UI available at: https://deliberate-api.fly.dev/docs

## Example Use Cases

- **Business decisions**: "We should pivot from B2B to B2C"
- **Technical choices**: "We should rewrite the backend in Rust"
- **Hiring**: "We should hire contractors instead of full-time engineers"
- **Product**: "We should add AI features to our product"
- **Fun debates**: "Pineapple belongs on pizza"

## Architecture

```
┌─────────────────┐
│   Client App    │
└────────┬────────┘
         │ POST /v1/deliberate
         ▼
┌─────────────────┐      ┌─────────────────┐
│  Deliberate API │─────▶│   OpenRouter    │
│    (FastAPI)    │      │   (LLM Gateway) │
└────────┬────────┘      └─────────────────┘
         │
         │ Background task
         ▼
┌─────────────────┐
│  R1 → R2 → R3   │
│  Deliberation   │
└─────────────────┘
```

## License

MIT
