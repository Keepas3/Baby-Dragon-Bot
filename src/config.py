import os
import mysql.connector
from mysql.connector import pooling
import coc
from dotenv import load_dotenv

load_dotenv()

# --- Credentials ---
TOKEN = os.getenv('DISCORD_TOKEN2')
COC_EMAIL = os.getenv('COC_EMAIL')
COC_PASSWORD = os.getenv('COC_PASSWORD')

coc_client = None
db_pool = None  # 🚀 The dispatcher

def init_db_pool():
    """Initializes the connection pool with linked host/port logic."""
    global db_pool
    
    # 1. Linked Networking Logic
    internal_host = os.getenv("MYSQLHOST")
    if internal_host:
        host = internal_host
        port = "3306" # Internal networking ALWAYS uses 3306
        conn_type = "INTERNAL"
    else:
        host = os.getenv("RAILWAY_TCP_PROXY_DOMAIN", "localhost")
        port = os.getenv("RAILWAY_TCP_PROXY_PORT", "3306")
        conn_type = "PUBLIC/PROXY"

    print(f"📡 Initializing DB Pool ({conn_type}) at {host}:{port}...")

    db_config = {
        "host": host,
        "user": os.getenv("MYSQLUSER", "root"),
        "password": os.getenv("MYSQLPASSWORD"),
        "database": os.getenv("MYSQLDATABASE"),
        "port": int(port),
        "autocommit": True,
        "connect_timeout": 15
    }

    try:
        # Create a pool of 5 connections. 
        # If the DB restarts, the pool handles re-establishing connections.
        db_pool = pooling.MySQLConnectionPool(
            pool_name="dragon_pool",
            pool_size=5,
            **db_config
        )
    except Exception as e:
        print(f"❌ Failed to create DB pool: {e}")

def get_db_connection():
    """Gets a healthy connection from the pool."""
    global db_pool
    if db_pool is None:
        init_db_pool()
    
    try:
        return db_pool.get_connection()
    except:
        # If the pool is exhausted or DB is down, try re-initializing
        init_db_pool()
        return db_pool.get_connection()

def get_db_cursor():
    """Returns a buffered cursor from a pooled connection."""
    try:
        conn = get_db_connection()
        # The pool handles 'ping' logic. We just need the cursor.
        return conn.cursor(buffered=True)
    except Exception as e:
        print(f"⚠️ Cursor Error: {e}")
        return None

# --- CoC Initialization ---
async def initialize_coc():
    global coc_client
    try:
        new_client = coc.Client(key_names="Railway Bot")
        await new_client.login(COC_EMAIL, COC_PASSWORD)
        coc_client = new_client
        print("✅ CoC Client logged in.")
    except Exception as e:
        print(f"❌ CoC Login Failed: {e}")