"""MCP tools adapt the supplier REST API; credentials stay server-side."""
import os
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()
mcp = FastMCP('ModelCoffeeProtocol')


async def api_request(method: str, path: str, body: dict | None = None) -> dict | list:
    async with httpx.AsyncClient(base_url=os.getenv('VENDOR_API_URL', 'http://127.0.0.1:8000'),
                                 timeout=10, headers={'Authorization': 'Bearer ' + os.getenv('VENDOR_API_KEY', 'local-demo-token')}) as client:
        try:
            response = await client.request(method, path, json=body)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise ValueError(f'Supplier rejected the request (HTTP {exc.response.status_code})') from None
        except httpx.RequestError:
            raise ValueError('Supplier unavailable or outcome unknown. Do not blindly retry a quote mutation.') from None


@mcp.tool()
async def check_inventory() -> dict:
    """Get bean stock, consumption, lead time and whether the reorder point is reached."""
    return await api_request('GET', '/inventory')


@mcp.tool()
async def list_vendors() -> list:
    """List simulated roasters and delivery lead times; vendor IDs are required for quotes."""
    return await api_request('GET', '/vendors')


@mcp.tool()
async def request_quote(vendor: str, quantity_kg: int) -> dict:
    """Request a nonbinding quote for 5–500 kg of beans. Prices are USD cents. Does not buy anything."""
    return await api_request('POST', '/quotes', {'vendor': vendor, 'quantity_kg': quantity_kg})


@mcp.tool()
async def negotiate_quote(quote_id: str, unit_price_cents: int, shipping_cents: int) -> dict:
    """Offer a price per kg and shipping fee in USD cents. Supplier may counter; at most three rounds. No purchase."""
    return await api_request('POST', f'/quotes/{quote_id}/counteroffers',
                             {'unit_price_cents': unit_price_cents, 'shipping_cents': shipping_cents})


if __name__ == '__main__':
    mcp.run(transport='http', host='127.0.0.1', port=8001)
