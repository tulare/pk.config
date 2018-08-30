# -*- encoding: utf-8 -*-
from __future__ import (
    absolute_import,
    print_function, division,
    unicode_literals
)

__all__ = [ 'Configuration' ]

import os
import sys
import inspect
import sqlite3

from .exceptions import ConfigurationError, ConfigurationKeyError

# --------------------------------------------------------------------

def project_real_path(relative_path) :
    stack = inspect.stack()
    
    return os.path.realpath(
        os.path.abspath(
            os.path.join(
                os.path.split(
                    inspect.getfile(
                        stack[-1][0]
                    )
                )[0],
                relative_path
            )
        )
    )

# --------------------------------------------------------------------

PROJECT_PATH = project_real_path('.') 
CONFIG_DEFAULT_DATABASE = PROJECT_PATH + '/config.db'

# --------------------------------------------------------------------

class Configuration(object) :

    def __init__(self, database=CONFIG_DEFAULT_DATABASE) :

        self.database = database

        # creation table config si nécessaire
        with sqlite3.connect(self.database) as db :
            db.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key STRING PRIMARY KEY,
                    value STRING NOT NULL
                )
            """)

    @property        
    def items(self) :
        with sqlite3.connect(self.database) as db :
            # select
            cursor = db.execute("SELECT * FROM config")
            return dict(cursor.fetchall())

    @property
    def keys(self) :
        return set(self.items.keys())

    def get(self, key, default=None) :
        with sqlite3.connect(self.database) as db :
            cursor = db.execute(
                "SELECT value FROM config WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            if row :
                return row[0]            
            else :
                if default is None :
                    raise ConfigurationKeyError(key)
                return default
        
    def add(self, key, value) :
        with sqlite3.connect(self.database) as db :
            try :
                # insert
                cursor = db.execute(
                    "INSERT INTO config VALUES(? , ?)",
                    (key, value)
                )
            except sqlite3.IntegrityError as e :
                # update
                cursor = db.execute(
                    "UPDATE config SET value = ? WHERE key = ?",
                    (value, key)
                )
            finally :
                # commit
                db.commit()

            return cursor.rowcount
        
    def delete(self, key) :
        with sqlite3.connect(self.database) as db :
            try :
                # delete
                cursor = db.execute(
                    "DELETE FROM config WHERE key = ?",
                    (key,)
                )
            finally :
                # commit
                db.commit()

            return cursor.rowcount
        
    def checklist(self, key_list) :
        missing = set(key_list).difference(self.keys)
        if missing :
            raise ConfigurationError(missing)

        return True
        
    def checkfile(self, chkfile) :
        with open(chkfile, 'r') as fd :
            key_list = set(line.strip() for line in fd)
            return self.checklist(key_list)
            
