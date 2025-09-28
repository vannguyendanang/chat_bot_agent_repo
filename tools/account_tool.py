# import sqlite3
from langchain.tools import tool
# import mysql.connector
import os
from typing import Optional, List, Tuple
from langchain_core.tools import ToolException
import logging, traceback
from mysql.connector.pooling import MySQLConnectionPool
from app.constants import Constants


class AccountTool:
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

        self.pool = MySQLConnectionPool(
            pool_name="bank_pool",
            pool_size=5,
            **conn_kwargs,
        )        
        # self.pool = MySQLConnectionPool(
        #     pool_name="bank_pool",
        #     pool_size=5,
        #     host=Constants.DB_HOST, user=Constants.DB_USER, password=Constants.DB_PASS, database=Constants.DB_NAME,
        # )        

    def get_tool(self) -> Tuple:
        # conn = self.conn
        # Create a logger object to log different kinds of messages.(error, info, debug, etc.)
        # Name = "tools": all messages you emit with log.info(...), log.error(...), etc., are tagged with this logger name. 
        # For ex: ERROR:tools: update_bank_account failed....
        log = logging.getLogger("tools")
        
        @tool
        def update_bank_account(account_number: str,
                                address: Optional[str] = None, 
                                email: Optional[str] = None,
                                phone_number: Optional[str] = None) -> str:
            """Update the user's bank account."""
            conn = self.pool.get_connection()
            cursor = None
            try:
                # print("Co chay vao tool update_bank_account")
                cursor = conn.cursor()

                if not any([address, email, phone_number]):
                    # return "No field is provided to update."
                    raise ToolException("No field is provided to update.")
                
                # Build query dynamically based on provided parameters
                update_fields = []
                params = []

                if email:
                    update_fields.append("email = %s")
                    params.append(email)
                if phone_number:
                    update_fields.append("PhoneNumber = %s")
                    params.append(phone_number)
                if address:
                    update_fields.append("Address = %s")
                    params.append(address)
                if not update_fields:
                    return "No field is provided to update."

                # Add the account number to the parameters
                params.append(account_number)
                
                # Construct the SQL query
                query = f"UPDATE bankaccount SET {', '.join(update_fields)} where AccountNumber = %s"
                
                # tuple(params)  # Convert list to tuple for parameterized query
                # For ex: ["abc","555-1234", "123 Main St", "ACC001"] becomes ("abc", "555-1234", "123 Main St", "ACC001")
                cursor.execute(query, tuple(params))
                conn.commit()

                if cursor.rowcount == 0:
                    # return "No account found with the provided account number."
                    raise ToolException("No account found with the provided account number.")
                
                return f"Bank account updated to {account_number}"
            except Exception as e:
                # return f"Update failed: {e}"
                log.error("update_bank_account failed:\n%s", traceback.format_exc())
                raise ToolException(f"Update failed: {e}")
            finally:
                if cursor is not None: 
                    cursor.close()
                conn.close()  # returns connection to the pool
        # return update_bank_account

        @tool
        def account_balance(account_number: str) -> str:
            """Get the balance of the user's bank account."""
            conn = self.pool.get_connection()
            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT AccBalance FROM bankaccount WHERE AccountNumber = %s", (account_number,))
                result = cursor.fetchone()
                if result:
                    return f"Your account balance is {result[0]}"
                else:
                    return "No account found with the provided account number."
            except Exception as e:
                # return f"Failed to retrieve balance: {e}"
                raise ToolException(f"Failed to retrieve balance: {e}")
            finally:
                if cursor is not None: 
                    cursor.close()
                conn.close()  # returns connection to the pool
        return update_bank_account, account_balance
    
    # def close(self):
    #     """Close the database connection."""
    #     try:
    #         if self.conn and self.conn.is_connected():
    #             self.conn.close()
    #             # self.conn = None
    #     except Exception:
    #         pass  # Handle any exceptions that occur during close