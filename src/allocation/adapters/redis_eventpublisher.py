import redis
import logging
import json
from dataclasses import asdict

from allocation import config
from allocation.domain import events

logger = logging.getLogger(__name__)

r = redis.Redis(**config.get_redis_host_and_port())

def publish(channel, event: events.Event):
    logger.debug('Publishing event: %s on channel: %s', event, channel)
    r.publish(channel, json.dumps(asdict(event)))