import os
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

class DatabaseClient:
    """
    A professional-grade Database Client for TimescaleDB using SQLAlchemy.
    Uses an internal connection pool to handle multiple concurrent data requests.
    """
    _engine = None

    def __init__(self):
        """
        Initializes the SQLAlchemy engine if it doesn't already exist.
        """
        if DatabaseClient._engine is None:
            try:
                # Construct the Database URI
                user = os.getenv("DB_USER")
                password = os.getenv("DB_PASSWORD")
                host = os.getenv("DB_HOST")
                port = os.getenv("DB_PORT")
                dbname = os.getenv("DB_NAME")
                # db_uri = os.getenv("DATABASE_URL")
                
                db_uri = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
                
                # Create the engine with a connection pool
                DatabaseClient._engine = create_engine(
                    db_uri,
                    poolclass=QueuePool,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True  # Verifies connection is alive before using it
                )
                print("✅ SQLAlchemy Engine and Connection Pool established.")
            except Exception as e:
                print(f"❌ Error creating SQLAlchemy engine: {e}")

    def get_connection(self):
        """
        Returns a connection object from the SQLAlchemy engine.
        Note: In SQLAlchemy, 'engine' itself acts as a connectable.
        This method returns a connection for backward compatibility where needed.
        """
        return DatabaseClient._engine.connect()

    def get_engine(self):
        """
        Returns the raw SQLAlchemy engine. 
        Highly recommended for use with pd.read_sql().
        """
        return DatabaseClient._engine

    def execute_query(self, query, params=None):
        """
        Executes a query and returns results (for SELECT).
        Uses SQLAlchemy text() for SQL injection protection.
        """
        engine = self.get_engine()
        try:
            with engine.connect() as conn:
                # Wrap raw string in text() to ensure parameters are handled safely
                result = conn.execute(text(query), params or {})
                return result.fetchall()
        except Exception as e:
            print(f"❌ Query Execution Error: {e}")
            return None