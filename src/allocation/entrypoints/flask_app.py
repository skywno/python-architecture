from datetime import datetime
from flask import Flask, request

from allocation.adapters import orm
from allocation.service_layer import unit_of_work, messagebus, handler
from allocation.domain import commands
from allocation import views
from flask import jsonify

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
    messagebus.handle(cmd, unit_of_work.SqlAlchemyUnitOfWork())
    return "OK", 201


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    try:
        cmd = commands.Allocate(
            orderid=request.json["orderid"],
            sku=request.json["sku"],
            qty=request.json["qty"],
        )
        messagebus.handle(cmd, unit_of_work.SqlAlchemyUnitOfWork())
    except handler.InvalidSku as e:
        return {"message": str(e)}, 400

    return "OK", 202

@app.route("/change_batch_quantity", methods=["POST"])
def change_batch_quantity():
    cmd = commands.ChangeBatchQuantity(
        ref=request.json["ref"],
        qty=request.json["qty"],
    )
    try:
        messagebus.handle(cmd, unit_of_work.SqlAlchemyUnitOfWork())
        return "OK", 201
    except handler.InvalidBatchReference as e:
        return {"message": str(e)}, 400

@app.route("/allocations/<orderid>", methods=["GET"])
def allocations_view_endpoint(orderid):
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    result = views.allocations(orderid, uow)
    if not result:
        return 'not found', 404
    return jsonify(result), 200