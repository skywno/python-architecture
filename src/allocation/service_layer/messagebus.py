from allocation.domain import events
from typing import Dict, List, Callable, Type, Union, Optional
from allocation.adapters import email
from allocation.service_layer import unit_of_work
from allocation.domain import commands
from allocation.service_layer import handler as handlers
import logging
from tenacity import Retrying, RetryError, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

Message = Union[events.Event, commands.Command]


def handle(message: Message, uow: unit_of_work.AbstractUnitOfWork):
    queue = [message]
    while queue:
        message = queue.pop(0)
        if isinstance(message, events.Event):
            handle_event(message, queue, uow)
        elif isinstance(message, commands.Command):
            handle_command(message, queue, uow)

def handle_event(event: events.Event, queue: List[Message], uow: unit_of_work.AbstractUnitOfWork):
    for handler in HANDLERS[type(event)]:
        try:
            logger.debug("Handling event: %s with the handler: %s", event, handler)
            handler(event, uow)
            queue.extend(uow.collect_new_events())
        except Exception as e:
            logger.error("Exception handling event: %s with the handler: %s", event, handler, exc_info=True)
            continue

def handle_command(command: commands.Command, queue: List[Message], uow: unit_of_work.AbstractUnitOfWork):
    logger.debug('handling command: %s', command)
    try:
        handler = COMMAND_HANDLERS[type(command)]
        result = handler(command, uow)
        queue.extend(uow.collect_new_events())
        return result
    except Exception as e:
        logger.error("Exception handling command: %s with the handler: %s", command, handler)
        logger.exception(e)
        raise

HANDLERS : Dict[Type[events.Event], List[Callable[[events.Event], None]]] = {
    events.OutOfStock: [handlers.send_out_of_stock_notification],
    events.Allocated: [
        handlers.publish_allocated_event,
        handlers.add_allocation_to_read_model,
    ],
    events.Deallocated: [
        handlers.remove_allocation_from_read_model,
        handlers.reallocate,
    ]
}

COMMAND_HANDLERS: Dict[Type[commands.Command], Callable[[commands.Command], None]] = {
    commands.Allocate: handlers.allocate,
    commands.CreateBatch: handlers.add_batch,
    commands.ChangeBatchQuantity: handlers.change_batch_quantity,
}