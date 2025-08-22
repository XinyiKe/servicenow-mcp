import os
import json
import asyncio
import logging
import re
import ast

from basic_mcp_client import BasicMCPClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MCP_SSE_URL = os.environ.get("MCP_SSE_URL", "http://localhost:8080/sse")
SENSITIVE_KEYS = {"SERVICENOW_PASSWORD"}



async def call_tool_async(tool_name, args):
    client = BasicMCPClient()
    await client.connect(MCP_SSE_URL)
    try:
        result = await client.call_tool(tool_name, args)
        
        return result

    finally:
        await client.cleanup()
    
def parse_tool_args(args_raw):

    if not args_raw or not isinstance(args_raw, str):
        return {}

    args_raw = args_raw.strip()
    if args_raw.startswith("{") and args_raw.endswith("}"):
        args_raw = args_raw[1:-1]  # remove surrounding {}

    # Split by comma not inside quotes (we don't have quotes initially, so basic split works)
    parts = [p.strip() for p in args_raw.split(",")]
    result = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()

        if key in {"limit", "offset"} and re.fullmatch(r"-?\d+", value):
            value = int(value)
        else:
            value = str(value)

        result[key] = value

    return result
    
def lambda_handler(event, context):
    logger.info("Raw event from Bedrock:\n%s", json.dumps(event, indent=2))

    props = (
        event.get("requestBody", {})
             .get("content", {})
             .get("application/json", {})
             .get("properties", [])
    )

    props_dict = {item["name"]: item["value"] for item in props}

    tool_name = props_dict.get("tool")
    args_raw = props_dict.get("args")

    if not tool_name:
        return {
            "statusCode": 400,
            "body": json.dumps({"output": "Missing tool name"}),
            "headers": {"Content-Type": "application/json"}
        }

    # Parse `args` as JSON if possible
    try:
        """
        if isinstance(args_raw, dict):
            args = args_raw
        elif isinstance(args_raw, str):
            try:
                # Attempt to normalize non-JSON string like {limit=3}
                normalized = args_raw.strip()
                if normalized.startswith("{") and "=" in normalized:
                    # Convert {limit=3} → {"limit": 3}
                    normalized = re.sub(r'([a-zA-Z0-9_]+)=', r'"\1":', normalized)
                    normalized = re.sub(
                        r':\s*([^"\{\}\[\]0-9][^,\}]*)',
                        lambda m: ':"{}"'.format(m.group(1).strip()),
                        normalized
                    )
                    args = json.loads(normalized)
                else:
                    args = json.loads(normalized)
            except Exception as e:
                logger.warning("Failed to parse tool args string '%s': %s", args_raw, str(e))
                args = {}
    
        else:
            args = {}
    """
        args = parse_tool_args(args_raw)
    except Exception:
        logger.warning("Failed to parse tool args; using empty args")
        args = {}
    print(f"Tool name: {tool_name}, Args: {args}")

    output = asyncio.run(call_tool_async(tool_name, args))
    print(f"Tool call output: {output}")
    print(f"type(output): {type(output)}")  
    output_dict = json.loads(output) 
    print(f"type(output_dict): {type(output_dict)}") 
    response = {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": "servicenow_incident",
            "apiPath": "/call-tool",
            "httpMethod": "POST",
            "httpStatusCode": 200,
            "responseBody": {
            "application/json": {
                "body": output_dict
            }
        }
    },

    }

        # Log the full response (pretty-printed)
    logger.info("Lambda response:\n%s", json.dumps(response, indent=2))

    return response
