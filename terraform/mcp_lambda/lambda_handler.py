import os
import json
import asyncio
from basic_mcp_client import BasicMCPClient

MCP_SSE_URL = os.environ.get("MCP_SSE_URL", "http://localhost:8080/sse")

def lambda_handler(event, context):
    """
    Bedrock passes:
    {
      "parameters": {
        "tool": "list_incidents",
        "args": {
          "limit": 3,
          "offset": 1
        }
      }
    }
    """
    params = event.get("parameters", {})
    tool_name = params.get("tool")
    args = params.get("args", {})

    if not tool_name:
        return {"error": "Missing tool name"}

    # Convert any non-string args to strings for compatibility
    args = {k: str(v) for k, v in args.items()}

    async def call_tool():
        client = BasicMCPClient()
        await client.connect(MCP_SSE_URL)
        try:
            result = await client.session.call_tool(tool_name, args)
            return result.content if hasattr(result, 'content') else str(result)
        finally:
            await client.cleanup()

    try:
        result = asyncio.run(call_tool())
        return {
            "output": result  # return raw tool response
        }
    except Exception as e:
        return {
            "error": str(e)
        }
