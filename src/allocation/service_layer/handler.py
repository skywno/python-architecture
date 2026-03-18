from __future__ import annotations
from typing import Optional
from datetime import date

from click.core import batch

from allocation.domain import model
from allocation.domain.model import OrderLine
from allocation.service_layer import unit_of_work
from allocation.domain import events
from allocation.adapters import email
from typing import Dict, List, Callable, Type

class InvalidSku(Exception):
    pass

class InvalidBatchReference(Exception):
    pass

def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def send_out_of_stock_notification(event: events.OutOfStock, uow: unit_of_work.AbstractUnitOfWork):
    email.send_mail(
        "stock@made.com",
        f"Out of stock for {event.sku}"
    )


def add_batch(event: events.BatchCreated, uow: unit_of_work.AbstractUnitOfWork):
    with uow:
        product = uow.products.get(sku=event.sku)
        if product is None:
            product = model.Product(sku=event.sku, batches=[])
            uow.products.add(product)
        product.batches.append(model.Batch(ref=event.ref, sku=event.sku, qty=event.qty, eta=event.eta))
        uow.commit()


def allocate(
    event: events.AllocationRequired,
    uow: unit_of_work.AbstractUnitOfWork,
) -> str | None:
    line = OrderLine(event.orderid, event.sku, event.qty)
    with uow:
        product = uow.products.get(sku=event.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {event.sku}")
        batchref = product.allocate(line)
        uow.commit()
    return batchref

def change_batch_quantity(
    event: events.BatchQuantityChanged, 
    uow: unit_of_work.AbstractUnitOfWork
) -> None:
    with uow:
        product = uow.products.get_by_batchref(batchref=event.ref)
        if product is None:
            raise InvalidBatchReference(f"Invalid batch reference {event.ref}")
        product.change_batch_quantity(event.ref, event.qty)
        uow.commit()
