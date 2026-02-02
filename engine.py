"""Deliberation engine - runs R1-R3 protocol."""

import asyncio
import json
import logging
import re
from typing import Callable, Awaitable

from models import (
    Job, JobStatus, DeliberationResult, AgentOutput, RoundOutput,
    Confidence,
)
from openrouter import get_client, OpenRouterError
from prompts import build_r1_prompt, build_r2_prompt, build_r3_prompt, AGENT_LABELS

logger = logging.getLogger(__name__)

# Default models for diverse perspectives
DEFAULT_MODELS = [
    "anthropic/claude-haiku-4.5",
    "liquid/lfm-2.5-1.2b-thinking:free",
    "google/gemini-3-flash-preview",
]


class DeliberationEngine:
    """Runs the 3-round deliberation protocol."""

    def __init__(self):
        self.client = get_client()

    async def run_deliberation(
        self,
        job: Job,
        on_progress: Callable[[int, str], Awaitable[None]] | None = None,
    ) -> DeliberationResult:
        """
        Run full R1-R3 deliberation.

        Args:
            job: The job containing thesis, context, and model config
            on_progress: Optional callback(round_number, status_message)

        Returns:
            DeliberationResult with verdict and divergences
        """
        total_tokens = 0

        # R1: Independent Analysis (parallel)
        if on_progress:
            await on_progress(1, "Running independent analysis...")

        r1_outputs = await self._run_r1(job)
        total_tokens += sum(o.tokens_used for o in r1_outputs)

        # R2: Cross-Reading (parallel)
        if on_progress:
            await on_progress(2, "Running cross-reading...")

        r2_outputs = await self._run_r2(job, r1_outputs)
        total_tokens += sum(o.tokens_used for o in r2_outputs)

        # R3: Synthesis
        if on_progress:
            await on_progress(3, "Synthesizing results...")

        result = await self._run_r3(job, r2_outputs)
        result.tokens_used = total_tokens + result.tokens_used

        return result

    async def _call_agent(
        self,
        model: str,
        prompt: str,
        agent_id: str,
    ) -> AgentOutput:
        """Call a single agent."""
        try:
            result = await self.client.chat_completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.7,
            )

            return AgentOutput(
                agent_id=agent_id,
                model=model,
                content=result["content"],
                tokens_used=result["tokens_used"],
            )

        except OpenRouterError as e:
            logger.error(f"Agent {agent_id} ({model}) failed: {e}")
            return AgentOutput(
                agent_id=agent_id,
                model=model,
                content=f"[Error: {str(e)}]",
                tokens_used=0,
            )

    async def _run_r1(self, job: Job) -> list[AgentOutput]:
        """Run R1: Independent Analysis in parallel with role-based perspectives."""
        tasks = [
            self._call_agent(
                model,
                build_r1_prompt(job.thesis, role_index=i, context=job.context),
                f"agent_{i}"
            )
            for i, model in enumerate(job.models)
        ]

        outputs = await asyncio.gather(*tasks)
        logger.info(f"R1 complete: {len(outputs)} agents")
        return list(outputs)

    async def _run_r2(self, job: Job, r1_outputs: list[AgentOutput]) -> list[AgentOutput]:
        """Run R2: Cross-Reading in parallel."""
        tasks = []

        for i, own_output in enumerate(r1_outputs):
            # Build anonymized list of other outputs
            other_outputs = [
                (AGENT_LABELS[j], out.content)
                for j, out in enumerate(r1_outputs)
                if j != i
            ]

            prompt = build_r2_prompt(job.thesis, own_output.content, other_outputs)
            tasks.append(self._call_agent(job.models[i], prompt, f"agent_{i}"))

        outputs = await asyncio.gather(*tasks)
        logger.info(f"R2 complete: {len(outputs)} agents")
        return list(outputs)

    async def _run_r3(self, job: Job, r2_outputs: list[AgentOutput]) -> DeliberationResult:
        """Run R3: Synthesis and parse structured output."""
        # Build synthesis prompt
        all_outputs = [
            (AGENT_LABELS[i], out.content)
            for i, out in enumerate(r2_outputs)
        ]
        prompt = build_r3_prompt(job.thesis, all_outputs)

        # Use first model for synthesis (or could use a specific model)
        result = await self.client.chat_completion(
            model=job.models[0],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.5,  # Lower temp for synthesis
        )

        content = result["content"]
        tokens_used = result["tokens_used"]

        # Parse structured JSON from response
        parsed = self._parse_synthesis(content)
        parsed.tokens_used = tokens_used

        logger.info(f"R3 complete: answer={parsed.answer[:50]}...")
        return parsed

    def _parse_synthesis(self, content: str) -> DeliberationResult:
        """Extract structured result from R3 synthesis."""
        # Try to find JSON block - handle nested braces properly
        json_match = re.search(r"```json\s*(\{[\s\S]*\})\s*```", content)

        if json_match:
            json_str = json_match.group(1)
            # Find the balanced closing brace
            json_str = self._extract_balanced_json(json_str)
            try:
                data = json.loads(json_str)
                return self._build_result_from_json(data)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse synthesis JSON: {e}")
                logger.debug(f"JSON string was: {json_str[:500]}...")

        # Try finding raw JSON without markdown
        raw_match = re.search(r'\{\s*"answer"[\s\S]*\}', content)
        if raw_match:
            try:
                json_str = self._extract_balanced_json(raw_match.group(0))
                data = json.loads(json_str)
                return self._build_result_from_json(data)
            except json.JSONDecodeError:
                pass

        # Fallback: extract what we can from the text
        logger.warning("Could not parse JSON, using fallback extraction")
        return self._build_fallback_result(content)

    def _extract_balanced_json(self, s: str) -> str:
        """Extract balanced JSON object from string."""
        depth = 0
        start = s.index('{')
        for i, c in enumerate(s[start:], start):
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return s[start:i+1]
        return s  # Return as-is if unbalanced

    def _build_result_from_json(self, data: dict) -> DeliberationResult:
        """Build result from parsed JSON."""
        return DeliberationResult(
            answer=data.get("answer", "No answer provided"),
            confidence=Confidence(data.get("confidence", "medium")),
            support=data.get("support", []),
            concerns=data.get("concerns", []),
            conviction=data.get("conviction", ""),
            open_questions=data.get("open_questions", []),
        )

    def _build_fallback_result(self, content: str) -> DeliberationResult:
        """Build result from unstructured text."""
        # Simple extraction - first paragraph as answer
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        answer = paragraphs[0] if paragraphs else "Analysis complete - see full content"

        return DeliberationResult(
            answer=answer[:500],
            confidence=Confidence.MEDIUM,
            support=[],
            concerns=[],
            conviction="",
            open_questions=[],
        )
