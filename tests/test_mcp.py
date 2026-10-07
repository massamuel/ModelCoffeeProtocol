import httpx
from fastmcp import Client
from modelcoffee.api import app, quotes
from modelcoffee import mcp_server


async def test_mcp_discovery_and_api_negotiation(monkeypatch):
    quotes.clear()
    monkeypatch.setenv('VENDOR_API_KEY', 'local-demo-token')
    original = httpx.AsyncClient
    def local_client(**kwargs):
        return original(transport=httpx.ASGITransport(app=app), **kwargs)
    monkeypatch.setattr(mcp_server.httpx, 'AsyncClient', local_client)
    async with Client(mcp_server.mcp) as client:
        tools = await client.list_tools()
        assert {t.name for t in tools} == {'check_inventory', 'list_vendors', 'request_quote', 'negotiate_quote'}
        inventory = await client.call_tool('check_inventory', {})
        assert inventory.data['needs_reorder'] is True
        quote = await client.call_tool('request_quote', {'vendor': 'roaster-a', 'quantity_kg': 25})
        result = await client.call_tool('negotiate_quote', {'quote_id': quote.data['id'], 'unit_price_cents': 2200, 'shipping_cents': 0})
        assert result.data['total_cents'] == 55000
        assert result.data['order_placed'] is False
