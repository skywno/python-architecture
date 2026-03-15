import abc
from allocation.domain import model


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
    @abc.abstractmethod
    def add(self, product: model.Product):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, sku: str) -> model.Product:
        raise NotImplementedError


class SqlAlchemyProductRepository(AbstractProductRepository):
    def __init__(self, session):
        self.session = session

    def add(self, product):
        self.session.add(product)

    def get(self, sku):
        return self.session.query(model.Product).filter_by(sku=sku).first()