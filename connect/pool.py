#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (c) 2021 , Inc. All Rights Reserved
This module provide configure file management service in i18n environment.

Authors: lijunfeng(lijunfeng01@)
Date: 2021/10/21 14:54:06
"""
import time
import threading

import psycopg2

from src.connect import connection
from src import config_util as cfg

from loguru import logger
from psycopg2.pool import PoolError
from psycopg2 import extensions as _ext


class AbstractConnectionPool(object):
    """Generic connection pool, base by psycopg2.pool.AbstractConnectionPool"""

    def __init__(self, max_conn, expires, **kwargs):
        """Initialize

        Args:
                max_conn: max connections num
                expires: max expiration time
        """
        self._pool = []
        self._used = {}
        self._conn_keys = {}
        self._time_used = {}
        self._keys = 0
        self._disposed = False
        self.max_conn = max_conn
        self.expires = expires
        self._config = kwargs

    def _connect(self, key=None):
        """connect to pg server"""
        conn = psycopg2.connect(**self._config)

        if key is not None:
            self._used[key] = conn
            self._conn_keys[id(conn)] = key
            self._time_used[id(conn)] = int(time.time())
        else:
            self._pool.append(conn)

        return conn

    def _release(self, conn, remove_from_pool=False):
        """release connection
        
        Args:
                conn: db connection
                remove_from_pool: close connection or save as idle connection
        """
        if remove_from_pool and conn in self._pool:
            self._pool.remove(conn)
            del self._time_used[id(conn)]

    def _gen_key(self):
        """generator a unique key"""
        self._keys += 1
        return self._keys

    def _get_conn(self, key=None):
        """get a free connection"""
        if self._disposed:
            raise PoolError('Connection pool has benn disposed')

        self._release_expired_connections()

        if key is None:
            key = self._gen_key()
        if key in self._used:
            return self._used[key]
        
        if self._pool:
            self._used[key] = conn = self._pool.pop()
            self._conn_keys[id(conn)] = key
            self._time_used[id(conn)] = int(time.time())
            return conn
        else:
            if len(self._used) == self.max_conn:
                raise PoolError('Connection pool exhausted')
            return self._connect(key)

    def _release_expired_connections(self):
        """close expired connections"""
        now = int(time.time())
        for conn in self._pool:
            interval = now - self._time_used[id(conn)]
            if interval >= self.expires:
                self._release(conn, True)
    
    def _put_conn(self, conn, key=None, close=False, silently=False):
        """put away a connection and check expires"""
        if self._disposed:
            if silently:
                return
            raise PoolError('Connection pool is disposed')
        
        if key is None:
            key = self._conn_keys.get(id(conn))
        if not key:
            raise PoolError('Connection is un-keyed')

        if len(self._pool) < self.max_conn and not close:
            if not conn.closed:
                if not conn.closed:
                    status = conn.get_transaction_status()
                    if status == _ext.TRANSACTION_STATUS_UNKNOWN:
                        # server connection lost
                        logger.info('Connection lost. Closing %s' % conn)
                        self._release(conn)
                    elif status != _ext.TRANSACTION_STATUS_IDLE:
                        # connection in error or in transaction
                        conn.rollback()
                        self._pool.append(conn)
                    else:
                        # regular idle connection
                        self._pool.append(conn)
                # If the connection is closed, we just discard it.
        else:
            self._release(conn)

        self._release_expired_connections()

        if not self._disposed or key in self._used:
            del self._used[key]
            del self._conn_keys[id(conn)]
    
    def _release_all(self):
        """close all connections"""
        if self._disposed:
            raise PoolError('Connection pool has been disposed')

        close_conns = self._pool + list(self._used.values())
        for conn in close_conns:
            try:
                conn.close()
            except:
                pass
        
        self._disposed = True
        self.pool, self._used = [], {}

    def __del__(self):
        self._release_all()


class ThreadedConnectionPool(AbstractConnectionPool):
    """A connection pool that works with the threading module."""

    def __init__(self, max_conn, expires, **kwargs):
        """Initialize threading lock"""
        super().__init__(max_conn, expires, **kwargs)
        self._lock = threading.Lock()
        self._threading_conns = {}

    def get_conn(self, key=None):
        """get a free connection"""
        self._lock.acquire()
        try:
            return self._get_conn(key)
        finally:
            self._lock.release()

    def put_conn(self, conn, key=None, close=False, silently=False):
        """put away a connection"""
        self._lock.acquire()
        try:
            self._put_conn(conn, key, close, silently)
        finally:
            self._lock.release()

    def release_expired_connections(self):
        """close expired connections"""
        self._lock.acquire()
        try:
            self._release_expired_connections()
        finally:
            self._lock.release()

    def release_all(self):
        """Release all connections (even the one currently in use.)"""
        self._lock.acquire()
        try:
            self._release_all()
        finally:
            self._lock.release()

    def __enter__(self):
        tid = threading.get_ident()
        if threading.get_ident() not in self._threading_conns:
            self._threading_conns[tid] = None
        if self._threading_conns[tid] is None:
            self._threading_conns[tid] = connection.PgConnection(self)
        return self._threading_conns[tid]

    def __exit__(self, exc_type, exc_value, traceback):
        tid = threading.get_ident()
        pg_conn = self._threading_conns[tid]
        try:
            if not isinstance(exc_value, Exception):
                pg_conn.commit()
            else:
                pg_conn.rollback()
        except Exception as e:
            logger.error(f"exit conn error: {e}")
        finally:
            pg_conn._cursor.close()
            pg_conn._pool.put_conn(pg_conn._connection, silently=True)
            self._threading_conns[tid] = None