"""Prompt templates for R1-R3 deliberation."""

from datetime import date

MARKDOWN_INSTRUCTION = """

**Format your response using Markdown:**
- Use ## headings to organize sections
- Use **bold** for key points
- Use bullet points for clarity"""


def build_r1_prompt(thesis: str, context: str | None = None) -> str:
    """Build R1 (Independent Analysis) prompt."""
    todays_date = date.today().strftime("%B %d, %Y")

    context_section = ""
    if context:
        context_section = f"""
---
**CONTEXT**
{context}
---
"""

    return f"""You are analyzing the following thesis:
---
{thesis}
---
{context_section}
Today's date: {todays_date}

Provide your independent analysis. Consider:
- Strengths and weaknesses of the argument
- Missing considerations
- Potential risks and opportunities
- Evidence that would strengthen or weaken the thesis
- Key assumptions and dependencies

Be thorough but concise. Focus on your highest-conviction insights.
{MARKDOWN_INSTRUCTION}"""


def build_r2_prompt(
    thesis: str,
    own_r1_output: str,
    other_outputs: list[tuple[str, str]],  # [(label, output), ...]
) -> str:
    """Build R2 (Cross-Reading) prompt."""
    others_section = ""
    for label, output in other_outputs:
        others_section += f"\n**{label}:**\n---\n{output}\n---\n"

    return f"""Original thesis:
---
{thesis}
---

Your R1 analysis:
---
{own_r1_output}
---

Other agents' analyses:
{others_section}

Review the other analyses and identify:
1. **Points of agreement** - Where do all analyses converge?
2. **Points of disagreement** - Where do analyses diverge? Why?
3. **New considerations** - What did others raise that you find compelling?
4. **Rebuttals** - What do you disagree with and why?

{MARKDOWN_INSTRUCTION}"""


def build_r3_prompt(
    thesis: str,
    all_r2_outputs: list[tuple[str, str]],
) -> str:
    """Build R3 (Synthesis) prompt with structured output."""
    outputs_section = ""
    for label, output in all_r2_outputs:
        outputs_section += f"\n**{label}:**\n---\n{output}\n---\n"

    return f"""Original thesis:
---
{thesis}
---

All R2 outputs (after cross-reading):
{outputs_section}

Synthesize the deliberation into a final verdict.

Your response MUST end with a structured JSON block in exactly this format:

```json
{{
  "verdict": "Your clear, actionable verdict on the thesis (1-2 sentences)",
  "confidence": "high" | "medium" | "low",
  "reasoning": "The key reasoning behind your verdict (2-3 sentences)",
  "key_agreements": [
    "First point all agents agreed on",
    "Second point of consensus",
    "..."
  ],
  "divergences": [
    {{
      "topic": "Topic of disagreement",
      "description": "What the disagreement is about",
      "positions": [
        {{"view": "First agent's view", "confidence": "high|medium|low"}},
        {{"view": "Second agent's view", "confidence": "high|medium|low"}},
        {{"view": "Third agent's view", "confidence": "high|medium|low"}}
      ]
    }}
  ]
}}
```

First, write your synthesis narrative, then end with the JSON block.
{MARKDOWN_INSTRUCTION}"""


# Agent labels for anonymization
AGENT_LABELS = ["Agent Alpha", "Agent Beta", "Agent Gamma"]
