import asyncio
import json
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client

class BasicMCPClient:
    def __init__(self):
        self.session = None
        self.exit_stack = AsyncExitStack()
        self._streams_context = None
        self._session_context = None

    async def connect(self, server_url: str):
        """Connect to MCP server with SSE"""
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        await self.session.initialize()
        print("Connected to MCP server")

    async def cleanup(self):
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def list_tools(self):
        response = await self.session.list_tools()
        tools = response.tools
        for idx, tool in enumerate(tools):
            print(f"[{idx}] {tool.name}: {tool.description}")
        return tools

    async def call_tool(self, tool_name: str, args: dict):
        print(f"\n Calling tool '{tool_name}' with args: {json.dumps(args)}")
        result = await self.session.call_tool(tool_name, args)
        if isinstance(result.content, list):
            texts = [c.text for c in result.content if hasattr(c, "text")]
            combined = "\n".join(texts)
        elif hasattr(result.content, "text"):
            combined = result.content.text
        else:
            combined = str(result.content)

        parsed = json.loads(combined)
        final_result = json.dumps(parsed, indent=2)
        return final_result



    async def chat_loop(self):
        print("MCP Client Started")
        tools = await self.list_tools()
        tool_map = {tool.name: tool for tool in tools}

        while True:
            try:
                tool_input = input("\nEnter tool name (or 'list', or 'quit'): ").strip()

                if tool_input == 'quit':
                    break
                elif tool_input == 'list':
                    tools = await self.list_tools()
                    tool_map = {tool.name: tool for tool in tools}
                    continue
                elif tool_input not in tool_map:
                    print("Tool not found. Try again.")
                    continue

                tool = tool_map[tool_input]
                schema = tool.inputSchema or {}

                args = {}
                for field, value in schema.get("properties", {}).items():
                    default = value.get("default", "")
                    user_value = input(f"Enter value for '{field}' (type: {value.get('type', 'string')}): ")
                    args[field] = user_value or default

                await self.call_tool(tool.name, args)

            except Exception as e:
                print(f"Error: {e}")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python basic_mcp_client.py <http://localhost:8080/sse>")
        sys.exit(1)

    server_url = sys.argv[1]
    client = BasicMCPClient()
    try:
        await client.connect(server_url)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
