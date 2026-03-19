from allocation.service_layer import unit_of_work
from sqlalchemy import text

def allocations(orderid: str, uow: unit_of_work.SqlAlchemyUnitOfWork):
    with uow:
        results = list(uow.session.execute(
            text(
                "SELECT sku, batchref" 
                " FROM allocations_view" 
                " WHERE orderid = :orderid"),
            dict(orderid=orderid),
        ))
        return [{'sku': sku, 'batchref': batchref} for sku, batchref in results]