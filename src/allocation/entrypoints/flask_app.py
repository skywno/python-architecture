from datetime import datetime
from flask import Flask, request

from allocation.adapters import orm
from allocation.service_layer import unit_of_work, messagebus, handler
from allocation.domain import commands

app = Flask(__name__)
orm.start_mappers()


@app.route("/add_batch", methods=["POST"])
def add_batch():
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()
    cmd = commands.CreateBatch(
        ref=request.json["ref"],
        sku=request.json["sku"],
        qty=request.json["qty"],
        eta=eta,
    )
    results = messagebus.handle(cmd, unit_of_work.SqlAlchemyUnitOfWork())
    batchref = results[0]
    return {"batchref": batchref}, 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    try:
        cmd = commands.Allocate(
            orderid=request.json["orderid"],
            sku=request.json["sku"],
            qty=request.json["qty"],
        )
        results = messagebus.handle(cmd, unit_of_work.SqlAlchemyUnitOfWork())
        batchref = results[0]
    except handler.InvalidSku as e:
        return {"message": str(e)}, 400

    return {"batchref": batchref}, 201

@app.route("/change_batch_quantity", methods=["POST"])
def change_batch_quantity():
    cmd = commands.ChangeBatchQuantity(
        ref=request.json["ref"],
        qty=request.json["qty"],
    )
    try:
        results = messagebus.handle(cmd, unit_of_work.SqlAlchemyUnitOfWork())
        return {"message": "Batch quantity changed"}, 201
    except handler.InvalidBatchReference as e:
        return {"message": str(e)}, 400