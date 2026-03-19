from unittest import mock
import pytest
from allocation.adapters import repository
from allocation.service_layer import messagebus, unit_of_work
from allocation.domain import model, events, commands
from allocation.service_layer import handler

from datetime import date

class FakeProductRepository(repository.AbstractProductRepository):
    def __init__(self, products):
        super().__init__()
        self._products = set[model.Product](products) 

    def _add(self, product: model.Product):
        self._products.add(product)

    def _get(self, sku):
        return next((p for p in self._products if p.sku == sku), None)
    
    def _get_by_batchref(self, batchref):
        return next((
            p for p in self._products for b in p.batches
            if b.reference == batchref
        ), None)


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
        event = commands.CreateBatch(ref="b1", sku="CRUNCHY-ARMCHAIR", qty=100, eta=None)
        messagebus.handle(event, uow)
        assert uow.products.get(sku="CRUNCHY-ARMCHAIR") is not None
        assert uow.committed

    def test_add_batch_for_existing_product(self):
        uow = FakeUnitOfWork()
        event = commands.CreateBatch(ref="b1", sku="CRUNCHY-ARMCHAIR", qty=100, eta=None)
        messagebus.handle(event, uow)
        event = commands.CreateBatch(ref="b2", sku="CRUNCHY-ARMCHAIR", qty=100, eta=None)
        messagebus.handle(event, uow)
        assert set(uow.products.get(sku="CRUNCHY-ARMCHAIR").batches) == {model.Batch("b1", "CRUNCHY-ARMCHAIR", 100, None), model.Batch("b2", "CRUNCHY-ARMCHAIR", 100, None)}   
        assert uow.committed

class TestAllocate:

    def test_allocate_returns_allocation(self,sqlite_session_factory):
        uow = unit_of_work.SqlAlchemyUnitOfWork(sqlite_session_factory)
        cmd = commands.CreateBatch(ref="batch1", sku="COMPLICATED-LAMP", qty=100, eta=None)
        messagebus.handle(cmd, uow)
        cmd = commands.Allocate(orderid="o1", sku="COMPLICATED-LAMP", qty=10)
        messagebus.handle(cmd, uow)
        result = uow.products.get(sku="COMPLICATED-LAMP").batches[0].reference
        assert result == "batch1"

    def test_allocate_errors_for_invalid_sku(self,sqlite_session_factory):
        uow = unit_of_work.SqlAlchemyUnitOfWork(sqlite_session_factory)
        event = commands.CreateBatch(ref="b1", sku="AREALSKU", qty=100, eta=None)
        messagebus.handle(event, uow)

        with pytest.raises(handler.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
            cmd = commands.Allocate(orderid="o1", sku="NONEXISTENTSKU", qty=10)
            messagebus.handle(cmd, uow)

    def test_allocate_commits(self,sqlite_session_factory):
        uow = unit_of_work.SqlAlchemyUnitOfWork(sqlite_session_factory)
        event = commands.CreateBatch(ref="b1", sku="OMINOUS-MIRROR", qty=100, eta=None)
        messagebus.handle(event, uow)
        cmd = commands.Allocate(orderid="o1", sku="OMINOUS-MIRROR", qty=10)
        messagebus.handle(cmd, uow)

class TestSendEmailOnOutOfStockError:
    def test_send_email_on_out_of_stock_error(self):
        uow = FakeUnitOfWork()
        cmd = commands.CreateBatch(ref="b1", sku="POPULAR-CHURTAIN", qty=9, eta=None)
        messagebus.handle(cmd, uow)

        with mock.patch("allocation.adapters.email.send_mail") as mock_send_mail:
            cmd = commands.Allocate(orderid="o1", sku="POPULAR-CHURTAIN", qty=10)
            messagebus.handle(cmd, uow)
            assert mock_send_mail.call_args == mock.call(
                "stock@made.com", 
                "Out of stock for POPULAR-CHURTAIN"
            )

class TestChangeBatchQuantity:
    def test_changes_available_quantity(self,sqlite_session_factory):
        uow = unit_of_work.SqlAlchemyUnitOfWork(sqlite_session_factory)
        cmd = commands.CreateBatch(ref="b1", sku="OMINOUS-MIRROR", qty=100, eta=None)
        messagebus.handle(cmd, uow)
        [batch] = uow.products.get(sku="OMINOUS-MIRROR").batches
        assert batch.available_quantity == 100

        cmd = commands.ChangeBatchQuantity(ref="b1", qty=90)
        messagebus.handle(cmd, uow)
        [batch] = uow.products.get(sku="OMINOUS-MIRROR").batches
        assert batch.available_quantity == 90
    
    def test_reallocates_if_necessary(self,sqlite_session_factory):
        uow = unit_of_work.SqlAlchemyUnitOfWork(sqlite_session_factory)
        command_history = [
            commands.CreateBatch(ref="b1", sku="OMINOUS-MIRROR", qty=100, eta=None),
            commands.CreateBatch(ref="b2", sku="OMINOUS-MIRROR", qty=100, eta=date.today()),
            commands.Allocate(orderid="o1", sku="OMINOUS-MIRROR", qty=40),
            commands.Allocate(orderid="o2", sku="OMINOUS-MIRROR", qty=40)
        ]
        for cmd in command_history:
            messagebus.handle(cmd, uow)
        [batch1, batch2] = uow.products.get(sku="OMINOUS-MIRROR").batches
        assert batch1.available_quantity == 20
        assert batch2.available_quantity == 100
        
        cmd = commands.ChangeBatchQuantity(ref="b1", qty=50)
        messagebus.handle(cmd, uow)
        [batch1, batch2] = uow.products.get(sku="OMINOUS-MIRROR").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 60