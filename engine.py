"""Deliberation engine - runs R1-R3 protocol."""

import asyncio
import json
import logging
import re
from typing import Callable, Awaitable

from models import (
    Job, JobStatus, DeliberationResult, AgentOutput, RoundOutput,
    Divergence, Position, Confidence,
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
        """Run R1: Independent Analysis in parallel."""
        prompt = build_r1_prompt(job.thesis, job.context)

        tasks = [
            self._call_agent(model, prompt, f"agent_{i}")
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

        logger.info(f"R3 complete: verdict={parsed.verdict[:50]}...")
        return parsed

    def _parse_synthesis(self, content: str) -> DeliberationResult:
        """Extract structured result from R3 synthesis."""
        # Try to find JSON block
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)

        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return self._build_result_from_json(data)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse synthesis JSON: {e}")

        # Fallback: extract what we can from the text
        return self._build_fallback_result(content)

    def _build_result_from_json(self, data: dict) -> DeliberationResult:
        """Build result from parsed JSON."""
        # Parse divergences
        divergences = []
        for div in data.get("divergences", []):
            positions = [
                Position(
                    view=p.get("view", ""),
                    confidence=Confidence(p.get("confidence", "medium")),
                )
                for p in div.get("positions", [])
            ]
            divergences.append(Divergence(
                topic=div.get("topic", ""),
                description=div.get("description", ""),
                positions=positions,
            ))

        return DeliberationResult(
            verdict=data.get("verdict", "No verdict provided"),
            confidence=Confidence(data.get("confidence", "medium")),
            reasoning=data.get("reasoning", ""),
            key_agreements=data.get("key_agreements", []),
            divergences=divergences,
        )

    def _build_fallback_result(self, content: str) -> DeliberationResult:
        """Build result from unstructured text."""
        # Simple extraction - first paragraph as verdict
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        verdict = paragraphs[0] if paragraphs else "Analysis complete - see full content"

        return DeliberationResult(
            verdict=verdict[:500],  # Limit length
            confidence=Confidence.MEDIUM,
            reasoning="See full synthesis for details.",
            key_agreements=[],
            divergences=[],
        )
