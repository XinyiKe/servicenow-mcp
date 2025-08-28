import asyncio
import json
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client
from servicenow_mcp.server import Server
from servicenow_mcp.utils.config import AuthConfig, AuthType, BasicAuthConfig, ServerConfig
from servicenow_mcp.auth.auth_manager import AuthManager



class BasicMCPClient:
    def __init__(self, instance_url: str, username: str, password: str):
        self.session = None
        self.exit_stack = AsyncExitStack()
        self._streams_context = None
        self._session_context = None
        self.auth_header = None

        auth_config = AuthConfig(
                    type=AuthType.BASIC,
                    basic=BasicAuthConfig(username=username, password=password)
                )
        self.config = ServerConfig(
            instance_url=instance_url,
            auth=auth_config
        )

        # Initialize AuthManager (client side only)
        self.auth_manager = AuthManager(self.config.auth)
        # Extract headers for server calls
        self.auth_header = self.auth_manager.get_headers()

    async def connect(self, server_url: str):
    #async def connect(self, server_url: str, username: str, password: str):
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
           
        if self.auth_header:
        # inject auth header into args
            args["headers"] = self.auth_header
            print(f"Injected auth header into args: {self.auth_header}")

        print(f"\nCalling tool '{tool_name}' with args: {args}")
        result = await self.session.call_tool(tool_name, args)
        if isinstance(result.content, list):
            texts = [c.text for c in result.content if hasattr(c, "text")]
            combined = "\n".join(texts)
        elif hasattr(result.content, "text"):
            combined = result.content.text
        else:
            combined = str(result.content)

        try:
            parsed = json.loads(combined)
            final_result = json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            final_result = combined

        print(f"Tool result:\n{final_result}")
        return final_result

        #parsed = json.loads(combined)
        #print("Raw result content:", result.content)
        #final_result = json.dumps(parsed, indent=2)
        #print(f"Tool result:\n{final_result}")
        #return final_result



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
    if len(sys.argv) < 4:
        print("Usage: python basic_mcp_client.py <http://localhost:8080/sse>")
        sys.exit(1)

    instance_url = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]

    client = BasicMCPClient(instance_url, username, password)
    try:
        await client.connect(instance_url)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
