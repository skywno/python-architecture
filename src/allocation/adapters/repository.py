import abc
from allocation.domain import model
from typing import Set

# class AbstractBatchRepository(abc.ABC):
#     @abc.abstractmethod
#     def add(self, batch: model.Batch):
#         raise NotImplementedError

#     @abc.abstractmethod
#     def get(self, reference) -> model.Batch:
#         raise NotImplementedError


# class SqlAlchemyBatchRepository(AbstractBatchRepository):
#     def __init__(self, session):
#         self.session = session

#     def add(self, batch):
#         self.session.add(batch)

#     def get(self, reference):
#         return self.session.query(model.Batch).filter_by(reference=reference).one()

#     def list(self):
#         return self.session.query(model.Batch).all()

class AbstractProductRepository(abc.ABC):

    def __init__(self):
        self.seen: Set[model.Product] = set()

    def add(self, product: model.Product):
        self._add(product)
        self.seen.add(product)

    def get(self, sku: str) -> model.Product:
        product = self._get(sku)
        if product:
            self.seen.add(product)
        return product

    def get_by_batchref(self, batchref: str) -> model.Product:
        product = self._get_by_batchref(batchref)
        if product:
            self.seen.add(product)
        return product

    @abc.abstractmethod
    def _add(self, product: model.Product):
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, sku: str) -> model.Product:
        raise NotImplementedError

    @abc.abstractmethod
    def _get_by_batchref(self, batchref: str) -> model.Product:
        raise NotImplementedError


class SqlAlchemyProductRepository(AbstractProductRepository):
    def __init__(self, session):
        super().__init__()
        self.session = session

    def _add(self, product):
        self.session.add(product)

    def _get(self, sku):
        return self.session.query(model.Product).filter_by(sku=sku).first()

    def _get_by_batchref(self, batchref):
        return self.session.query(model.Product) \
            .join(model.Batch) \
            .filter(model.Batch.reference == batchref) \
            .first()