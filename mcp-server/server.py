#!/usr/bin/env python3
"""MCP Server for Deliberate API."""

import asyncio
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

API_URL = "https://deliberate-api.fly.dev"
API_KEY = "xyz-123-154"

server = Server("deliberate")


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="deliberate",
            description="Submit a thesis for multi-agent AI deliberation. Returns a structured verdict with agreements and divergences from 3 AI agents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "thesis": {
                        "type": "string",
                        "description": "The thesis or idea to deliberate on"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional additional context"
                    }
                },
                "required": ["thesis"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != "deliberate":
        raise ValueError(f"Unknown tool: {name}")

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=300) as client:
        # Submit job
        resp = await client.post(
            f"{API_URL}/v1/deliberate",
            headers=headers,
            json={"thesis": arguments["thesis"], "context": arguments.get("context")}
        )
        resp.raise_for_status()
        job = resp.json()
        job_id = job["job_id"]

        # Poll for result
        while True:
            resp = await client.get(
                f"{API_URL}/v1/jobs/{job_id}",
                headers=headers
            )
            resp.raise_for_status()
            status = resp.json()

            if status["status"] == "completed":
                result = status["result"]
                output = f"""## Verdict
{result['verdict']}

**Confidence**: {result['confidence']}

## Reasoning
{result['reasoning']}

## Key Agreements
"""
                for agreement in result["key_agreements"]:
                    output += f"- {agreement}\n"

                output += "\n## Divergences\n"
                for div in result["divergences"]:
                    output += f"\n### {div['topic']}\n{div['description']}\n"
                    for pos in div["positions"]:
                        output += f"- {pos['view']} (confidence: {pos['confidence']})\n"

                output += f"\n---\n*Tokens used: {result['tokens_used']} | Rounds: {result['rounds_completed']}*"

                return [TextContent(type="text", text=output)]

            elif status["status"] == "failed":
                return [TextContent(type="text", text=f"Deliberation failed: {status.get('error', 'Unknown error')}")]

            await asyncio.sleep(5)


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
