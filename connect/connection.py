#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (c) 2021 Baidu.com, Inc. All Rights Reserved
This module provide configure file management service in i18n environment.

Authors: lijunfeng(lijunfeng01@baidu.com)
Date: 2021/10/21 14:54:06
"""
from psycopg2.extras import NamedTupleCursor

class PgConnection(object):
    """postgres connection"""

    _connection = None
    _cursor = None
    _cursor_factory = None
    _pool = None

    def __init__(self, pool):
        self._cursor_factory = NamedTupleCursor
        self._pool = pool
        self._connect()

    def _connect(self):
        """get connection"""
        try:
            self._connection = self._pool.get_conn()
            self._cursor = self._connection.cursor(cursor_factory=self._cursor_factory)
        except Exception as e:
            raise e

    def execute(self, sql, params=None):
        """execute a raw query"""
        try:
            self._cursor.execute(sql, params)
        except Exception as e:
            raise e
        
        return self._cursor

    def fetchone(self, sql, params):
        """get single result"""
        cur = self.execute(sql, params)
        return cur.fetchone()

    def fetchall(self, sql, params):
        """get all result"""
        cur = self.execute(sql, params)
        return cur.fetchall()
    
    def execute_returning(self, sql, params):
        """execute with returning"""
        cur = self.execute(sql, params)
        return cur.fetchall()
    
    def execute_rowcount(self, sql, params):
        """execute with rowcount"""
        cur = self.execute(sql, params)
        return cur.rowcount

    def commit(self):
        """commit"""
        return self._connection.commit()
    
    def rollback(self):
        """rollback"""
        return self._connection.rollback()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not isinstance(exc_value, Exception):
            self.commit()
        else:
            self.rollback()

        self._cursor.close()
        self._pool.put_conn(self._connection, silently=True)