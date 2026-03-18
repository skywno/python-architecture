import uuid
import pytest
import requests

from allocation import config

from ..random_refs import random_sku, random_batchref, random_orderid
from . import api_client

@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_happy_path_returns_201_and_allocated_batch():
    sku, othersku = random_sku(), random_sku("other")
    earlybatch = random_batchref(1)
    laterbatch = random_batchref(2)
    otherbatch = random_batchref(3)
    api_client.post_to_add_batch(laterbatch, sku, 100, "2011-01-02")
    api_client.post_to_add_batch(earlybatch, sku, 100, "2011-01-01")
    api_client.post_to_add_batch(otherbatch, othersku, 100, None)

    r = api_client.post_to_allocate(random_orderid(), sku, 3)

    assert r.status_code == 201
    assert r.json()["batchref"] == earlybatch


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_returns_400_and_error_message():
    unknown_sku, orderid = random_sku(), random_orderid()
    data = {"orderid": orderid, "sku": unknown_sku, "qty": 20}
    url = config.get_api_url()
    r = requests.post(f"{url}/allocate", json=data)
    assert r.status_code == 400
    assert r.json()["message"] == f"Invalid sku {unknown_sku}"

@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_out_of_stock_fails_with_200_and_None_batchref():
    sku = random_sku()
    batch = random_batchref(1)
    api_client.post_to_add_batch(batch, sku, 10, "2011-01-01")

    r = api_client.post_to_allocate(random_orderid(), sku, 9)

    assert r.status_code == 201
    assert r.json()["batchref"] == batch

    # try to allocate again
    r = api_client.post_to_allocate(random_orderid(), sku, 9)
    assert r.status_code == 201
    assert r.json()["batchref"] == None
