"""Prompt templates for R1-R3 deliberation."""

from datetime import date

MARKDOWN_INSTRUCTION = """

**Format your response using Markdown:**
- Use ## headings to organize sections
- Use **bold** for key points
- Use bullet points for clarity"""

# Role-based agent definitions
AGENT_ROLES = [
    ("Optimist", "Focus on why this could succeed, work, or be true. Steel-man the strongest case."),
    ("Constructive Skeptic", "Focus on failure modes, risks, and reasons for doubt. Things that would need to be true for this to work. Do not engage in stakeholder theatre"),
    ("Analyst", "Focus on evidence, data, and empirical patterns. Be quantitative where possible. Ignore stakeholder theatre")
]

# Agent labels for anonymization in R2/R3
AGENT_LABELS = ["Agent Alpha", "Agent Beta", "Agent Gamma"]


def build_r1_prompt(thesis: str, role_index: int, context: str | None = None) -> str:
    """Build R1 (Independent Analysis) prompt with role-based perspective."""
    role_name, role_description = AGENT_ROLES[role_index]
    todays_date = date.today().strftime("%B %d, %Y")

    context_section = ""
    if context:
        context_section = f"""

**Additional Context:**
{context}
"""

    return f"""You are Agent {role_name}: {role_description}

Today's date: {todays_date}

Analyze this query from your perspective:
---
{thesis}
---
{context_section}
Provide your analysis covering:
- Your assessment/answer
- Your highest-conviction supporting points (2-4)
- Your highest-conviction concerns or counterpoints (2-4)
- Critical assumptions in your reasoning
- What evidence would change your view

Be direct and specific. Prioritize insight over comprehensiveness.
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

    return f"""Original query:
---
{thesis}
---

Your R1 analysis:
---
{own_r1_output}
---

Other agents' analyses:
{others_section}

Your task:
1. Identify the single strongest point made by another agent that challenges your R1 view - quote it directly and respond
2. Identify one significant consideration you missed - explain why it matters
3. State one point where you have higher conviction than the other agents - defend it with specific reasoning

Be substantive. Vague agreement or disagreement is not useful.
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

Synthesize the deliberation into a comprehensive final verdict.

IMPORTANT: Provide DETAILED, SUBSTANTIVE responses. Do not summarize or abbreviate.

Your response MUST end with a structured JSON block in exactly this format:

```json
{{
  "verdict": "Your clear, actionable verdict on the thesis. Be specific and detailed - at least 3-4 sentences explaining the bottom-line conclusion and its key qualifications.",
  "confidence": "high" | "medium" | "low",
  "reasoning": "Comprehensive reasoning behind your verdict. This should be a substantial paragraph (150-250 words) that synthesizes the key arguments, explains why certain factors were weighted more heavily, addresses the strongest counterarguments, and justifies the confidence level. Do NOT say 'see above' or 'as discussed' - provide the full reasoning here.",
  "key_agreements": [
    "First substantive point all agents agreed on - be specific about what exactly they agreed on and why it matters",
    "Second point of consensus with specific details",
    "Third point of agreement",
    "Fourth point if applicable",
    "Fifth point if applicable",
    "Include at least 4-6 meaningful agreements"
  ],
  "divergences": [
    {{
      "topic": "Specific topic of disagreement",
      "description": "Detailed description of what the disagreement is about, why it matters, and what's at stake (2-3 sentences minimum)",
      "positions": [
        {{"view": "First agent's detailed position - include their reasoning and key evidence (2-3 sentences)", "confidence": "high|medium|low"}},
        {{"view": "Second agent's detailed position with reasoning (2-3 sentences)", "confidence": "high|medium|low"}},
        {{"view": "Third agent's detailed position with reasoning (2-3 sentences)", "confidence": "high|medium|low"}}
      ]
    }},
    {{
      "topic": "Second area of divergence",
      "description": "Detailed description",
      "positions": [...]
    }}
  ]
}}
```

Include at least 3-5 divergences if they exist. Be thorough and substantive throughout.

First, write your synthesis narrative (at least 500 words), then end with the JSON block.
{MARKDOWN_INSTRUCTION}"""
