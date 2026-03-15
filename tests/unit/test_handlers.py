from unittest import mock
import pytest
from allocation.adapters import repository
from allocation.service_layer import messagebus, unit_of_work
from allocation.domain import model, events
from allocation.service_layer import handler


class FakeProductRepository(repository.AbstractProductRepository):
    def __init__(self, products):
        super().__init__()
        self._products = set[model.Product](products) 

    def _add(self, product: model.Product):
        self._products.add(product)

    def _get(self, sku):
        return next((p for p in self._products if p.sku == sku), None)

class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.products = FakeProductRepository([])
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self):
        pass


class TestAddBatch:

    def test_add_batch_for_new_product(self):
        uow = FakeUnitOfWork()
        event = events.BatchCreated(ref="b1", sku="CRUNCHY-ARMCHAIR", qty=100, eta=None)
        messagebus.handle(event, uow)
        assert uow.products.get(sku="CRUNCHY-ARMCHAIR") is not None
        assert uow.committed

    def test_add_batch_for_existing_product(self):
        uow = FakeUnitOfWork()
        event = events.BatchCreated(ref="b1", sku="CRUNCHY-ARMCHAIR", qty=100, eta=None)
        messagebus.handle(event, uow)
        event = events.BatchCreated(ref="b2", sku="CRUNCHY-ARMCHAIR", qty=100, eta=None)
        messagebus.handle(event, uow)
        assert set(uow.products.get(sku="CRUNCHY-ARMCHAIR").batches) == {model.Batch("b1", "CRUNCHY-ARMCHAIR", 100, None), model.Batch("b2", "CRUNCHY-ARMCHAIR", 100, None)}   
        assert uow.committed

class TestAllocate:

    def test_allocate_returns_allocation(self):
        uow = FakeUnitOfWork()
        event = events.BatchCreated(ref="batch1", sku="COMPLICATED-LAMP", qty=100, eta=None)
        messagebus.handle(event, uow)
        event = events.AllocationRequired(orderid="o1", sku="COMPLICATED-LAMP", qty=10)
        messagebus.handle(event, uow)
        result = uow.products.get(sku="COMPLICATED-LAMP").batches[0].reference
        assert result == "batch1"


    def test_allocate_errors_for_invalid_sku(self):
        uow = FakeUnitOfWork()
        event = events.BatchCreated(ref="b1", sku="AREALSKU", qty=100, eta=None)
        messagebus.handle(event, uow)

        with pytest.raises(handler.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
            event = events.AllocationRequired(orderid="o1", sku="NONEXISTENTSKU", qty=10)
            messagebus.handle(event, uow)


    def test_allocate_commits(self):
        uow = FakeUnitOfWork()
        event = events.BatchCreated(ref="b1", sku="OMINOUS-MIRROR", qty=100, eta=None)
        messagebus.handle(event, uow)
        event = events.AllocationRequired(orderid="o1", sku="OMINOUS-MIRROR", qty=10)
        messagebus.handle(event, uow)
        assert uow.committed

class TestSendEmailOnOutOfStockError:
    def test_send_email_on_out_of_stock_error(self):
        uow = FakeUnitOfWork()
        event = events.BatchCreated(ref="b1", sku="POPULAR-CHURTAIN", qty=9, eta=None)
        messagebus.handle(event, uow)

        with mock.patch("allocation.adapters.email.send_mail") as mock_send_mail:
            event = events.AllocationRequired(orderid="o1", sku="POPULAR-CHURTAIN", qty=10)
            messagebus.handle(event, uow)
            assert mock_send_mail.call_args == mock.call(
                "stock@made.com", 
                "Out of stock for POPULAR-CHURTAIN"
            )