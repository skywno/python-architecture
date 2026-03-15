from allocation.domain.events import Event, OutOfStock
from typing import Dict, List, Callable, Type
from allocation.adapters import email

def handle(event: Event):
    for handler in HANDLERS[type(event)]:
        handler(event)

def send_out_of_stock_notification(event: OutOfStock):
    email.send_mail(
        "stock@made.com",
        f"Out of stock for {event.sku}"
    )

HANDLERS : Dict[Type[Event], List[Callable[[Event], None]]] = {
    OutOfStock: [send_out_of_stock_notification],
}