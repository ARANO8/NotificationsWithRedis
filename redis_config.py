import redis

def get_redis_connection():
    """Conectar a Redis (puerto 6379 por defecto)."""
    return redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
