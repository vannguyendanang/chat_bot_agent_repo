
from langchain.tools import tool
from mysql.connector.pooling import MySQLConnectionPool
from langchain_core.tools import ToolException
from models.classifier import Classifier
from app.constants import Constants
import os 

class SupportPhone:
    """
    This class help tasks relating to supportive phone number in case virtal assistant can not anwser the user's query.
    """
    
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

    def get_tool(self):

        @tool
        def get_support_phone(question: str) -> str:
            # """Get the support phone number based on the category."""
            """Provides the direct phone number for the bank department best suited to handle the user's question.
            Use this tool ONLY if the information cannot be found in the knowledge base (lookup_pdf).
            
            Args:
                question (str): The original question from the user that could not be answered.
            """

            classifier_llm = Classifier()
            cat = classifier_llm.classify_query(question) 

            conn = self.pool.get_connection()
            cursor = None
            try:
                cursor = conn.cursor()
                query = "SELECT PhoneNum FROM phonemapping WHERE Category = %s"
                cursor.execute(query, (cat,))
                result = cursor.fetchone()
                if result:
                    return f"The support phone number for {cat} is {result[0]}."
                else:
                    return f"Sorry, I couldn't find a support phone number for the category '{cat}'."
            except Exception as e:
                # return f"An error occurred while retrieving the support phone number: {str(e)}"
                raise ToolException(f"Get_support_phone failed: {str(e)}")
            finally:
                if cursor is not None: 
                    cursor.close()
                conn.close()  # returns connection to the pool
        
        return get_support_phone