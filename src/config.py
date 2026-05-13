import os
import asyncio
import mysql.connector
from mysql.connector import pooling
import coc
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# --- 1. Discord Setup ---
TOKEN = os.getenv('DISCORD_TOKEN2')
COC_EMAIL = os.getenv('COC_EMAIL')
COC_PASSWORD = os.getenv('COC_PASSWORD')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 2. Global States ---
coc_client = None
db_pool = None  

# --- 3. Database Pooling Logic ---
def init_db_pool():
    """Initializes the connection pool with linked host/port logic."""
    global db_pool
    
    internal_host = os.getenv("MYSQLHOST")
    if internal_host:
        host = internal_host
        port = "3306" 
        conn_type = "INTERNAL"
    else:
        host = os.getenv("RAILWAY_TCP_PROXY_DOMAIN", "localhost")
        port = os.getenv("RAILWAY_TCP_PROXY_PORT", "3306")
        conn_type = "PUBLIC/PROXY"

    print(f"📡 Attempting DB Pool Init ({conn_type}) at {host}:{port}...")

    db_config = {
        "host": host,
        "user": os.getenv("MYSQLUSER", "root"),
        "password": os.getenv("MYSQLPASSWORD"),
        "database": os.getenv("MYSQLDATABASE"),
        "port": int(port),
        "autocommit": True,
        "connect_timeout": 20 # 🚀 Increased for Railway cold starts
    }

    try:
        db_pool = pooling.MySQLConnectionPool(
            pool_name="dragon_pool",
            pool_size=5,
            **db_config
        )
        print("✅ DB Pool successfully initialized.")
    except Exception as e:
        print(f"❌ Pool Init Failed: {e}")
        db_pool = None

def get_db_connection():
    global db_pool
    if db_pool is None:
        init_db_pool()
    
    if db_pool:
        try:
            return db_pool.get_connection()
        except Exception as e:
            print(f"⚠️ Pool connection error: {e}")
            init_db_pool() # Try to reset pool
            return db_pool.get_connection() if db_pool else None
    return None

def get_db_cursor():
    """Synchronous cursor getter for basic commands."""
    conn = get_db_connection()
    return conn.cursor(buffered=True) if conn else None

# --- 4. The "Safe" Async Cursor (Restored) ---
async def get_safe_cursor(retries=5, delay=10):
    """
    Handles the 'Cold Start' problem by retrying connections.
    Used by background tasks like war/raid reminders.
    """
    for attempt in range(retries):
        try:
            cursor = get_db_cursor()
            if cursor:
                return cursor
        except Exception:
            pass
        
        if attempt < retries - 1:
            print(f"⚠️ DB Warming up... (Attempt {attempt+1}/{retries})")
            await asyncio.sleep(delay)
    
    print("❌ get_safe_cursor exhausted all retries.")
    return None

# --- 5. CoC Initialization ---
async def initialize_coc():
    global coc_client
    try:
        new_client = coc.Client(key_names="Railway Bot")
        await new_client.login(COC_EMAIL, COC_PASSWORD)
        coc_client = new_client
        print("✅ CoC Client logged in.")
    except Exception as e:
        print(f"❌ CoC Login Failed: {e}")