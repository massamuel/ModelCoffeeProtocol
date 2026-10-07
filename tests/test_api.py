import pytest
from fastapi.testclient import TestClient
from modelcoffee.api import app, quotes

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('VENDOR_API_KEY', 'test-token')
    quotes.clear()
    with TestClient(app, headers={'Authorization': 'Bearer test-token'}) as client:
        yield client


def test_permissions_and_validation(client):
    assert client.get('/inventory', headers={'Authorization': 'Bearer wrong'}).status_code == 401
    assert client.post('/quotes', json={'vendor': 'unknown', 'quantity_kg': 25}).status_code == 422
    assert client.post('/quotes', json={'vendor': 'roaster-a', 'quantity_kg': -1}).status_code == 422


def test_reorder_signal(client):
    data = client.get('/inventory').json()
    assert data['days_remaining'] == 4
    assert data['needs_reorder'] is True
    assert data['reorder_point_kg'] == 18


def test_counteroffer_floor_and_limit(client):
    quote = client.post('/quotes', json={'vendor': 'roaster-a', 'quantity_kg': 25}).json()
    url = f"/quotes/{quote['id']}/counteroffers"
    offer = {'unit_price_cents': 2000, 'shipping_cents': 0}
    negotiated = client.post(url, json=offer).json()
    assert negotiated['unit_price_cents'] == 2200
    assert negotiated['total_cents'] == 55000
    assert negotiated['order_placed'] is False
    assert client.post(url, json=offer).status_code == 200
    assert client.post(url, json=offer).status_code == 200
    assert client.post(url, json=offer).status_code == 409


def test_small_order_freight_and_unknown_quote(client):
    quote = client.post('/quotes', json={'vendor': 'roaster-b', 'quantity_kg': 5}).json()
    offer = {'unit_price_cents': 2300, 'shipping_cents': 0}
    data = client.post(f"/quotes/{quote['id']}/counteroffers", json=offer).json()
    assert data['shipping_cents'] == 800
    assert client.post('/quotes/missing/counteroffers', json=offer).status_code == 404
