import asyncio
import json
import sys
import traceback
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
        print(f"[INFO] Connecting to MCP SSE server at: {server_url}")
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        await self.session.initialize()
        print("[INFO] Connected to MCP server")

    async def cleanup(self):
        print("[INFO] Cleaning up MCP client...")
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)
        print("[INFO] Cleanup done")

    async def list_tools(self):
        print("[INFO] Fetching list of available tools...")
        response = await self.session.list_tools()
        tools = response.tools
        print(f"[INFO] Found {len(tools)} tools:")
        for idx, tool in enumerate(tools):
            # Log full tool info for debug
            print(f"  [{idx}] Name: {tool.name}\n"
                  f"      Description: {tool.description}\n"
                  f"      Input Schema: {json.dumps(tool.inputSchema, indent=2)}\n")
        return tools

    async def call_tool(self, tool_name: str, args: dict):
        print(f"\n[INFO] Calling tool '{tool_name}' with args:\n{json.dumps(args, indent=2)}")
        try:
            result = await self.session.call_tool(tool_name, args)
            # Log full raw content of result
            print(f"[INFO] Tool call result content:\n{result.content}")
        except Exception as e:
            print(f"[ERROR] Exception calling tool '{tool_name}': {e}")
            traceback.print_exc()

    async def chat_loop(self):
        print("\n🛠 MCP Client Started")
        tools = await self.list_tools()
        tool_map = {tool.name: tool for tool in tools}

        while True:
            try:
                tool_input = input("\nEnter tool name (or 'list', or 'quit'): ").strip()

                if tool_input == 'quit':
                    print("[INFO] Quitting MCP Client.")
                    break
                elif tool_input == 'list':
                    tools = await self.list_tools()
                    tool_map = {tool.name: tool for tool in tools}
                    continue
                elif tool_input not in tool_map:
                    print("[WARN] Tool not found. Try again.")
                    continue

                tool = tool_map[tool_input]
                schema = tool.inputSchema or {}
                print(f"[DEBUG] Input schema for tool '{tool_input}':\n{json.dumps(schema, indent=2)}")

                args = {}
                for field, value in schema.get("properties", {}).items():
                    default = value.get("default", "")
                    user_value = input(f"Enter value for '{field}' (type: {value.get('type', 'string')}): ")
                    final_value = user_value or default
                    args[field] = final_value
                    print(f"[DEBUG] Field '{field}': using value '{final_value}'")

                print(f"[DEBUG] Final argument dictionary to send:\n{json.dumps(args, indent=2)}")
                await self.call_tool(tool.name, args)

            except Exception as e:
                print(f"[ERROR] Unexpected error in chat loop: {e}")
                traceback.print_exc()

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
