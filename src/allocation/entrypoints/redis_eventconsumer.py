from allocation import config
from allocation.adapters import orm
from allocation.domain import commands
from allocation.service_layer import messagebus, unit_of_work

import json
import logging
import redis

logger = logging.getLogger(__name__)

r = redis.Redis(**config.get_redis_host_and_port())

def main():
    orm.start_mappers()
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe('change_batch_quantity')

    for message in pubsub.listen():
        handle_change_batch_quantity(message)


def handle_change_batch_quantity(message):
    logger.debug('Handling message: %s', message)
    data = json.loads(message['data'])
    cmd = commands.ChangeBatchQuantity(ref=data['batchref'], qty=data['qty'])
    messagebus.handle(cmd, unit_of_work.SqlAlchemyUnitOfWork())


if __name__ == "__main__":
    main()
