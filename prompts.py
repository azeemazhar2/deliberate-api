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

    return f"""Synthesize all analyses into a clear, actionable output.

Original query:
---
{thesis}
---

All prior analysis:
{outputs_section}

Output valid JSON only:
```json
{{
  "answer": "Direct response to the query, 200-400 words",
  "confidence": "high|medium|low",
  "support": ["3-5 key points supporting this answer"],
  "concerns": ["2-4 key risks or limitations"],
  "conviction": "What the agents most strongly agreed on",
  "open_questions": ["1-2 unresolved issues that matter most"]
}}
```

Prioritize clarity and actionability. Be definitive where agents converged, honest about uncertainty where they diverged."""
