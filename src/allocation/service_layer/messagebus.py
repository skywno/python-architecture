from allocation.domain import events
from typing import Dict, List, Callable, Type
from allocation.adapters import email
from allocation.service_layer import unit_of_work

from allocation.service_layer.handler import (
    send_out_of_stock_notification,
    add_batch,
    allocate,
    change_batch_quantity,
)

def handle(event: events.Event, uow: unit_of_work.AbstractUnitOfWork):
    results = []
    queue = [event]
    while queue:
        event = queue.pop(0)
        for handler in HANDLERS[type(event)]:
            result = handler(event, uow)
            results.append(result)
            queue.extend(uow.collect_new_events())
    return results

HANDLERS : Dict[Type[events.Event], List[Callable[[events.Event], None]]] = {
    events.OutOfStock: [send_out_of_stock_notification],
    events.BatchCreated: [add_batch],
    events.AllocationRequired: [allocate],
    events.BatchQuantityChanged: [change_batch_quantity],
}