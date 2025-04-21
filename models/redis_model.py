from redis_config import get_redis_connection
import json

redis_client = get_redis_connection()

REDIS_LIST_NAME = 'notificaciones_list'
REDIS_SORTED_SET_NAME = 'notificaciones_sorted_set'

def save_message_to_list(message):
    redis_client.lpush(REDIS_LIST_NAME, message)

def save_message_to_sorted_set(message, priority):
    redis_client.zadd(REDIS_SORTED_SET_NAME, {message: priority})

def get_list_messages():
    return redis_client.lrange(REDIS_LIST_NAME, 0, -1)

def get_sorted_set_messages():
    return redis_client.zrange(REDIS_SORTED_SET_NAME, 0, -1, withscores=True)

def publish_message(channel, message):
    redis_client.publish(channel, message)

def subscribe_to_channel(channel, callback):
    pubsub = redis_client.pubsub()
    pubsub.subscribe(channel)
    for message in pubsub.listen():
        if message['type'] == 'message':
            callback(message['data'])
