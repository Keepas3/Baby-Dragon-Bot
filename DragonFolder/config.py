import os
import mysql.connector
import coc
import discord
from discord.ext import commands

# Credentials
TOKEN = os.getenv('DISCORD_TOKEN2')
COC_EMAIL = os.getenv('COC_EMAIL')
COC_PASSWORD = os.getenv('COC_PASSWORD')

# Clients and Intents
coc_client = coc.Client(key_names="Railway Bot")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- THE MISSING FUNCTION ---
async def initialize_coc():
    """Handles login and automatic IP whitelisting."""
    try:
        await coc_client.login(COC_EMAIL, COC_PASSWORD)
        print("Successfully logged into CoC and updated API key.")
    except coc.InvalidCredentials as e:
        print(f"Failed to login to CoC: {e}")

# Database logic
def connect_db():
    host = os.getenv("RAILWAY_TCP_PROXY_DOMAIN", "localhost")
    user = os.getenv("MYSQLUSER", "root")
    password = os.getenv("MYSQLPASSWORD", os.getenv("MY_SQL_PASSWORD"))
    database = os.getenv("MYSQLDATABASE", os.getenv("MY_SQL_DATABASE2"))
    port = os.getenv("RAILWAY_TCP_PROXY_PORT", "3306")
    
    return mysql.connector.connect(
        host=host, user=user, password=password, 
        database=database, port=port, autocommit=True
    )

db_connection = None

def get_db_cursor():
    global db_connection
    if db_connection is None or not db_connection.is_connected():
        db_connection = connect_db()
    return db_connection.cursor()