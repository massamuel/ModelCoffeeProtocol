"""Scripted model checks agent/MCP plumbing, not natural-language quality."""
import httpx
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from modelcoffee.agent import build_agent
from modelcoffee.api import app, quotes
from modelcoffee import mcp_server


async def test_agent_discovers_and_calls_mcp_tools(monkeypatch):
    quotes.clear()
    monkeypatch.setenv('VENDOR_API_KEY', 'local-demo-token')
    original = httpx.AsyncClient
    monkeypatch.setattr(mcp_server.httpx, 'AsyncClient', lambda **kwargs:
                        original(transport=httpx.ASGITransport(app=app), **kwargs))
    step = 0
    async def scripted_model(messages, info):
        nonlocal step
        assert {tool.name for tool in info.function_tools} == {
            'check_inventory', 'list_vendors', 'request_quote', 'negotiate_quote'}
        step += 1
        if step == 1:
            return ModelResponse(parts=[ToolCallPart('check_inventory', {})])
        if step == 2:
            return ModelResponse(parts=[ToolCallPart('request_quote', {'vendor': 'roaster-a', 'quantity_kg': 25})])
        if step == 3:
            parts = [p for m in messages for p in m.parts if isinstance(p, ToolReturnPart) and p.tool_name == 'request_quote']
            content = parts[-1].content
            # MCP structured results are exposed to the model as dictionaries.
            if isinstance(content, list):
                import json
                content = json.loads(content[0]['text'])
            return ModelResponse(parts=[ToolCallPart('negotiate_quote', {
                'quote_id': content['id'], 'unit_price_cents': 2200, 'shipping_cents': 0})])
        return ModelResponse(parts=[TextPart('Review the simulated $550 quote. No order placed.')])
    agent = build_agent(model=FunctionModel(scripted_model), server=MCPToolset(mcp_server.mcp))
    async with agent:
        result = await agent.run('Compare 25 kg within $600, delivered within four days.')
    assert '$550' in result.output
    assert list(quotes.values())[0]['total_cents'] == 55000
