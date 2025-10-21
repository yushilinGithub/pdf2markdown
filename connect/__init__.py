"""
db
"""
from src import config_util as cfg
from src.connect.pool import ThreadedConnectionPool


config = {
    "database": cfg.PG_DATABASE,
    "user": cfg.PG_USERNAME,
    "password": cfg.PG_PASSWORD,
    "host": cfg.PG_HOST,
    "port": cfg.PG_PORT
}
conn_pool = ThreadedConnectionPool(10, 60, **config)