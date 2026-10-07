"""Local simulated supplier. Monetary amounts are integer USD cents."""
import os
from secrets import compare_digest
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title='ModelCoffeeProtocol Vendor API', version='0.1.0')
bearer = HTTPBearer()
quotes: dict[str, dict] = {}


def authorize(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    expected = os.getenv('VENDOR_API_KEY', 'local-demo-token')
    if not compare_digest(credentials.credentials, expected):
        raise HTTPException(401, 'Invalid supplier credentials')


class QuoteRequest(BaseModel):
    vendor: str = Field(pattern='^(roaster-a|roaster-b)$')
    quantity_kg: int = Field(ge=5, le=500)


class CounterOffer(BaseModel):
    unit_price_cents: int = Field(ge=1, le=100000)
    shipping_cents: int = Field(ge=0, le=100000)


@app.get('/health')
def health():
    return {'status': 'ok', 'mode': 'simulation'}


@app.get('/inventory', dependencies=[Depends(authorize)])
def inventory():
    stock, daily, lead, buffer = 12, 3, 4, 2
    return {'product': 'espresso beans', 'stock_kg': stock,
            'daily_usage_kg': daily, 'lead_time_days': lead,
            'safety_buffer_days': buffer, 'days_remaining': stock / daily,
            'reorder_point_kg': daily * (lead + buffer),
            'needs_reorder': stock <= daily * (lead + buffer)}


@app.get('/vendors', dependencies=[Depends(authorize)])
def vendors():
    return [{'id': 'roaster-a', 'name': 'Demo Roaster A', 'lead_time_days': 4},
            {'id': 'roaster-b', 'name': 'Demo Roaster B', 'lead_time_days': 3}]


@app.post('/quotes', dependencies=[Depends(authorize)])
def create_quote(request: QuoteRequest):
    price, shipping = (2400, 1800) if request.vendor == 'roaster-a' else (2500, 1000)
    quote = {'id': str(uuid4()), **request.model_dump(), 'unit_price_cents': price,
             'shipping_cents': shipping, 'lead_time_days': 4 if request.vendor == 'roaster-a' else 3,
             'rounds': 0, 'status': 'quoted',
             'simulation': True, 'order_placed': False}
    quote['total_cents'] = request.quantity_kg * price + shipping
    quotes[quote['id']] = quote
    return quote


@app.post('/quotes/{quote_id}/counteroffers', dependencies=[Depends(authorize)])
def negotiate(quote_id: str, offer: CounterOffer):
    if quote_id not in quotes:
        raise HTTPException(404, 'Quote not found')
    quote = quotes[quote_id]
    if quote['rounds'] >= 3:
        raise HTTPException(409, 'Negotiation limit reached; review current quote')
    floor = 2200 if quote['vendor'] == 'roaster-a' else 2300
    freight_floor = 0 if quote['quantity_kg'] >= 25 else 800
    # The supplier never raises the existing offer during negotiation.
    quote['unit_price_cents'] = min(quote['unit_price_cents'], max(floor, offer.unit_price_cents))
    quote['shipping_cents'] = min(quote['shipping_cents'], max(freight_floor, offer.shipping_cents))
    quote['total_cents'] = quote['quantity_kg'] * quote['unit_price_cents'] + quote['shipping_cents']
    quote['rounds'] += 1
    quote['status'] = 'counteroffer'
    return quote
