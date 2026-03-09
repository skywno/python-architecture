from __future__ import annotations

import model
from model import OrderLine
from repository import AbstractRepository


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


# Coupled to the model. Deprecated.
def allocate(line: OrderLine, repo: AbstractRepository, session) -> str:
    batches = repo.list()
    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")
    batchref = model.allocate(line, batches)
    session.commit()
    return batchref

# Decoupled from the model.
# def allocate(orderId: str, sku: str, qty: int, repo: AbstractRepository, session) -> str:
#     batches = repo.list()
#     if not is_valid_sku(sku, batches):
#         raise InvalidSku(f"Invalid sku {sku}")
#     batchref = model.allocate(model.OrderLine(orderId, sku, qty), batches)
#     session.commit()
#     return batchref