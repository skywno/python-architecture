from __future__ import annotations
from typing import Optional
from datetime import date

from click.core import batch
from allocation.adapters import redis_eventpublisher
from allocation.domain import model
from allocation.domain.model import OrderLine
from allocation.service_layer import unit_of_work
from allocation.domain import events, commands
from allocation.adapters import email
from typing import Dict, List, Callable, Type
from tenacity import retry, stop_after_attempt, wait_exponential

class InvalidSku(Exception):
    pass

class InvalidBatchReference(Exception):
    pass

def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def add_batch(cmd: commands.CreateBatch, uow: unit_of_work.AbstractUnitOfWork):
    with uow:
        product = uow.products.get(sku=cmd.sku)
        if product is None:
            product = model.Product(sku=cmd.sku, batches=[])
            uow.products.add(product)
        product.batches.append(model.Batch(ref=cmd.ref, sku=cmd.sku, qty=cmd.qty, eta=cmd.eta))
        uow.commit()


def allocate(
    cmd: commands.Allocate,
    uow: unit_of_work.AbstractUnitOfWork,
) -> str | None:
    line = OrderLine(cmd.orderid, cmd.sku, cmd.qty)
    with uow:
        product = uow.products.get(sku=cmd.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {cmd.sku}")
        batchref = product.allocate(line)
        uow.commit()
    return batchref


def change_batch_quantity(
    cmd: commands.ChangeBatchQuantity, 
    uow: unit_of_work.AbstractUnitOfWork
) -> None:
    with uow:
        product = uow.products.get_by_batchref(batchref=cmd.ref)
        if product is None:
            raise InvalidBatchReference(f"Invalid batch reference {cmd.ref}")
        product.change_batch_quantity(cmd.ref, cmd.qty)
        uow.commit()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(),
    reraise=True,
)
def send_out_of_stock_notification(event: events.OutOfStock, uow: unit_of_work.AbstractUnitOfWork):
    email.send_mail(
        "stock@made.com",
        f"Out of stock for {event.sku}"
    )

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(),
    reraise=True,
)
def publish_allocated_event(event: events.Allocated, uow: unit_of_work.AbstractUnitOfWork):
    redis_eventpublisher.publish('line_allocated', event)