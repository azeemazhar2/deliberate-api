# Deliberate API

Multi-agent deliberation service that stress-tests ideas through structured AI debate.

## How It Works

1. **R1 (Independent Analysis)**: 3 AI agents independently analyze your thesis
2. **R2 (Cross-Reading)**: Each agent reviews the others' analyses (anonymized)
3. **R3 (Synthesis)**: Produces a verdict with agreements and divergences

## Quick Start

```bash
# Install dependencies
pip install -e .

# Set environment variables
cp .env.example .env
# Edit .env with your keys

# Run locally
python main.py
```

## API Usage

### Start a Deliberation

```bash
curl -X POST https://your-api.com/v1/deliberate \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "thesis": "We should acquire CompanyX for $30M",
    "context": "We are a $50M ARR SaaS company looking to expand..."
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
curl https://your-api.com/v1/jobs/dlb_abc123 \
  -H "X-API-Key: your-key"
```

Response (when complete):
```json
{
  "job_id": "dlb_abc123",
  "status": "completed",
  "result": {
    "verdict": "Proceed with caution - valuation is fair but integration risks are significant",
    "confidence": "medium",
    "reasoning": "Two agents support the acquisition while one raises concerns about cultural fit...",
    "key_agreements": [
      "Market position is defensible",
      "Tech stack is compatible",
      "Team is strong"
    ],
    "divergences": [
      {
        "topic": "Valuation",
        "description": "Disagreement on whether $30M is fair",
        "positions": [
          {"view": "Fair given growth trajectory", "confidence": "high"},
          {"view": "Overpriced by 15-20%", "confidence": "medium"},
          {"view": "Undervalued given IP portfolio", "confidence": "low"}
        ]
      }
    ],
    "tokens_used": 45000
  }
}
```

## Deploy to AWS App Runner

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
docker build -t deliberate-api .
docker tag deliberate-api:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/deliberate-api:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/deliberate-api:latest

# Create App Runner service via console or CLI
aws apprunner create-service \
  --service-name deliberate-api \
  --source-configuration '{...}'
```

Set environment variables in App Runner:
- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `API_KEYS`: Comma-separated list of valid client API keys

## Configuration

### Custom Models

You can specify which models to use:

```json
{
  "thesis": "...",
  "models": [
    "anthropic/claude-sonnet-4-20250514",
    "openai/gpt-4o",
    "google/gemini-2.0-flash-001"
  ]
}
```

Defaults to a diverse set of Claude, GPT-4o, and Gemini.

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
