import os
import mysql.connector
import coc
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# Credentials
TOKEN = os.getenv('DISCORD_TOKEN2')
COC_EMAIL = os.getenv('COC_EMAIL')
COC_PASSWORD = os.getenv('COC_PASSWORD')

# 1. Initialize the Client
# In coc.py 4.0.0, we create the client instance first. 
# It will use these key_names to manage your API keys on the developer portal.
coc_client = coc.Client(key_names="Railway Bot")

intents = discord.Intents.default()
intents.message_content = True  # Required for prefix commands
intents.members = True          # Useful for tracking joins/leaves

bot = commands.Bot(command_prefix="!", intents=intents)

# 2. Asynchronous CoC Initialization
async def initialize_coc():
    """Handles the async login process required in v4.0.0."""
    try:
        # This will automatically handle IP changes by creating/updating keys
        await coc_client.login(COC_EMAIL, COC_PASSWORD)
        print("✅ CoC Client logged in and keys synchronized.")
    except coc.InvalidCredentials as e:
        print(f"❌ CoC Login Failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected CoC Error: {e}")

# 3. Robust Database logic
def connect_db():
    # Railway provides these variables automatically if you use their MySQL service
    host = os.getenv("MYSQLHOST", "localhost")
    user = os.getenv("MYSQLUSER", "root")
    password = os.getenv("MYSQLPASSWORD")
    database = os.getenv("MYSQLDATABASE")
    port = os.getenv("MYSQLPORT", "3306")
    
    return mysql.connector.connect(
        host=host, 
        user=user, 
        password=password, 
        database=database, 
        port=port, 
        autocommit=True
    )

db_connection = None

def get_db_cursor():
    global db_connection
    try:
        if db_connection is None or not db_connection.is_connected():
            db_connection = connect_db()
        return db_connection.cursor()
    except Exception as e:
        # This will now print the REAL error to your Railway logs
        print(f"CRITICAL DATABASE ERROR: {e}")
        raise e  # This will force the bot to show the error in the logs