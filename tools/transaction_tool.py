from mysql.connector.pooling import MySQLConnectionPool
# from typing import List
import logging, traceback
from langchain.tools import tool
from datetime import datetime
from langchain_core.tools import ToolException
from langsmith.run_helpers import traceable
# from app.server import APP_LOGGER  # or define a constant in one place
from app.constants import Constants
import pymysql
import os

log = logging.getLogger(f"{Constants.APP_LOGGER}.{__name__}")

class TransactionTool:

    def make_conn(self):
        db_user = os.environ["DB_USER"]
        db_pass = os.environ["DB_PASS"]
        db_name = os.environ["DB_NAME"]

        icn = os.environ.get("INSTANCE_CONNECTION_NAME")  # e.g. "triple-router-472320-d0:us-central1:bankbot-mysql"
        if icn:
            # Cloud Run + Cloud SQL unix socket
            unix_socket = f"/cloudsql/{icn}"
            return pymysql.connect(user=db_user, password=db_pass, db=db_name, unix_socket=unix_socket)

        # Fallback for local/dev (TCP)
        db_host = os.environ.get("DB_HOST", "127.0.0.1")
        db_port = int(os.environ.get("DB_PORT", "3306"))
        return pymysql.connect(user=db_user, password=db_pass, db=db_name, host=db_host, port=db_port)
        
    def __init__(self):
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

    
    def _parse_date_time(dt_str: str) -> datetime:
        # try Python's ISO parser first (handles 'T' or space, offsets, microseconds; not 'Z')
        s = dt_str.strip()
        if s.endswith("Z"):                   # make 'Z' acceptable
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s)  # e.g., '2025-05-04 13:00:30' or '2025-05-04T13:00:30'
        except ValueError:
            pass

        # fallback to a few explicit patterns
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S.%f",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        raise ToolException(
            "Invalid date time. Use ISO 8601 like '2025-05-04T13:00:30' "
            "or '2025-05-04 13:00:30' (optionally with timezone)."
        )

    def get_tool(self) -> str:

        # log = logging.getLogger("tools")
        # log = logging.getLogger("bankbot")
        # log = logging.getLogger(__name__) 

        @tool
        def get_list_transactions(account_number: str, start_date: str, end_date: str) -> str:
            # """View transaction details for a given account number within a date range."""
            """Return JSON with transactions within the date range."""

            if not account_number or not start_date or not end_date:
                raise ToolException("Account number, start date, and end date are required.")
            
            # Convert date time string into datetime object
            start_time = TransactionTool._parse_date_time(start_date)
            end_time = TransactionTool._parse_date_time(end_date)

            if start_time >= end_time:
                raise ToolException("Start date must be before end date.")
            
            conn = self.pool.get_connection()
            cursor = None
            try:
                cursor = conn.cursor()
                query = """
                    SELECT ReceiverFirstName, ReceiverLastName, TransDateTime, TransferContent, TransferStatus, TransferAmount
                    FROM banktransaction 
                    WHERE AccountNumber = %s AND TransDateTime BETWEEN %s AND %s
                    ORDER BY TransDateTime DESC
                """
                cursor.execute(query, (account_number, start_date, end_date))
                results = cursor.fetchall()
                if results:
                    transactions = [
                        f"""Receiver's first name: {row[0]}, receiver's last name: {row[1]}, transfer date time: {row[2]}, 
                        transfer content: {row[3]}, transfer status: {row[4]}, transfer amount: {row[5]}"""
                        for row in results
                    ]
                    return "Transactions:\n" + "\n".join(transactions)
                else:
                    return "No transactions found for the given criteria."
            except Exception as e:
                log.error("get_list_transactions failed:\n%s", traceback.format_exc())
                raise ToolException(f"It's failed to get list of transactions: {e}")
            finally:
                if cursor is not None:
                    cursor.close()
                conn.close()

        @tool
        @traceable(name="sql_dispute_update")
        def disputeTrans(account_number: str, transfer_date_time: str, receiver_firstname: str, receiver_lastname: str, transfer_amount: int) -> str:
            """Dispute user's transaction""" 
            conn = self.pool.get_connection()
            cursor = None
            log.info("account_number=%s", account_number)
            try:
                cursor = conn.cursor()
                if not account_number or not transfer_date_time or not receiver_firstname or not receiver_lastname or not transfer_amount:
                    raise ToolException("Account number, transfered date time, receiver's first name, receiver's last name, transfer amount are required.")
                
                transfered_dt = TransactionTool._parse_date_time(transfer_date_time)
                search_query = """
                    Select TransactionId from banktransaction where AccountNumber = %s and TransDateTime = %s and ReceiverFirstName = %s and 
                    ReceiverLastName = %s and TransferAmount = %s
                """
                search_params = (account_number, transfered_dt, receiver_firstname, receiver_lastname, transfer_amount)
                log.debug("Executing search SQL: %s | params=%r", search_query, search_params)
                # print("Executing search SQL:", search_query, "| params:", search_params)

                cursor.execute(search_query, search_params)
                result = cursor.fetchone()
                if not result:
                    return "No transaction found for the provided information."
                else:
                    update_query = """
                    Update banktransaction set TransferStatus = %s where TransactionId = %s
                """
                params = ('Disputed', result[0])
                log.debug("Executing update SQL: %s | params=%r", update_query, params)
                
                # print("Executing update SQL:", update_query, "| params:", params)
                cursor.execute(update_query, params)
                conn.commit()
                rowcount = cursor.rowcount
                log.debug("Executed. rowcount=%s", rowcount)
                if  rowcount== 0:
                    raise ToolException(f"No transaction found with provided Transaction Id {result[0]}")
                return f"Transaction has been disputed for account number {account_number}"
            except Exception as e:
                log.error("Dispute transaction is failed.\n%s", traceback.format_exc())
                raise ToolException(f"Dispute transaction is not successful: {e}")
            finally:
                if cursor is not None:
                    cursor.close()
                conn.close()
        return get_list_transactions, disputeTrans