import os
import json
import asyncio
import logging

from basic_mcp_client import BasicMCPClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MCP_SSE_URL = os.environ.get("MCP_SSE_URL", "http://localhost:8080/sse")
SENSITIVE_KEYS = {"SERVICENOW_PASSWORD"}

def redact_sensitive_data(data):
    if isinstance(data, dict):
        return {
            k: ("****" if k.lower() in SENSITIVE_KEYS else redact_sensitive_data(v))
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [redact_sensitive_data(i) for i in data]
    return data

async def call_tool_async(tool_name, args):
    client = BasicMCPClient()
    await client.connect(MCP_SSE_URL)
    try:
        result = await client.session.call_tool(tool_name, args)

        content = result.content
       
        if isinstance(content, list):
            return [item.get("text", str(item)) if isinstance(item, dict) else str(item) for item in content]
        elif isinstance(content, dict):
            return content.get("text", str(content))
        else:
            return str(content)
    finally:
        await client.cleanup()

def lambda_handler(event, context):
    params = event.get("parameters", {})
    tool_name = params.get("tool")
    args = params.get("args", {})

    if not tool_name:
        return {"error": "Missing tool name"}

   
    args = {k: str(v) for k, v in args.items()}
    redacted_args = redact_sensitive_data(args)
    logger.info(f"Calling tool '{tool_name}' with sanitized args: {json.dumps(redacted_args)}")

    try:
        output = asyncio.run(call_tool_async(tool_name, args))
        return {"output": output}
    except Exception as e:
        logger.exception("Tool execution failed")
        return {"error": str(e)}
