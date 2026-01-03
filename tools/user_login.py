# import sqlite3
# from langchain.tools import tool
# import mysql.connector
import os
# from typing import Optional, List, Tuple
from langchain_core.tools import ToolException
import logging, traceback
from mysql.connector.pooling import MySQLConnectionPool
# from app.constants import Constants


class UserLogin:
    def __init__(self):
        # self.conn = sqlite3.connect(db_path)
        # self._setup()
        # Mysql connection setup
        # self.conn = mysql.connector.connect(
        #     host="localhost",user="root",password="Admin25&@",database="bank_chatbot")
        db_user = os.environ["DB_USER"]
        db_pass = os.environ["DB_PASS"]
        db_name = os.environ["DB_NAME"]

        # If Cloud SQL is attached, Cloud Run sets INSTANCE_CONNECTION_NAME in your env.public.yaml
        icn = os.environ.get("INSTANCE_CONNECTION_NAME")  # e.g. "proj:us-central1:bankbot-mysql"

        if icn:
            # Use the Cloud SQL Unix socket on Cloud Run
            # NOTE: with mysql-connector, use 'unix_socket' (no host/port)
            conn_kwargs = dict(
                user=db_user,
                password=db_pass,
                database=db_name,
                unix_socket=f"/cloudsql/{icn}",
                connection_timeout=10,
            )
        else:
            # Local/dev or external MySQL over TCP
            db_host = os.environ.get("DB_HOST", "127.0.0.1")
            db_port = int(os.environ.get("DB_PORT", "3306"))
            conn_kwargs = dict(
                user=db_user,
                password=db_pass,
                database=db_name,
                host=db_host,
                port=db_port,
                connection_timeout=10,
            )
        # define a set of database connections that can be reused
        self.pool = MySQLConnectionPool(
            pool_name="bank_pool",
            # Maximum of 5 open DB connections
            # At most 5 concurrent requests can use the DB at once
            # Others wait until a connection is returned
            pool_size=5,
            **conn_kwargs,
        )   

    def check_login(self, account_number: str,
                    password: str) -> bool:
        """Validate user's account and password."""
        conn = self.pool.get_connection()
        cursor = None
        # Create a logger object to log different kinds of messages.(error, info, debug, etc.)
        # Name = "tools": all messages you emit with log.info(...), log.error(...), etc., are tagged with this logger name. 
        # For ex: ERROR:tools: update_bank_account failed....        
        log = logging.getLogger("tools")
        try:
            # print("Co chay vao tool check_login")
            cursor = conn.cursor()

            if not any([account_number, password]):
                # return "No field is provided to update."
                raise ToolException("No field is provided to check.")
            # print("Params:", (account_number, password))
            cursor.execute("Select * from bankaccount where AccountNumber = %s and Password = %s", (account_number, password))
            result = cursor.fetchone()
            
            if (result):
                # print("result True")
                return True
            else:
                # print("result false")
                return False
        except Exception as e:
            log.error("Account lookup failed:\n%s", traceback.format_exc())
            raise ToolException(f"Failed to retrieve user account: {e}")
        finally:
            if cursor is not None: 
                cursor.close()
            conn.close()  # returns connection to the pool


    