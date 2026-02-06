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


coc_client = None

intents = discord.Intents.default()
intents.message_content = True  # Required for prefix commands
intents.members = True          # Useful for tracking joins/leaves

bot = commands.Bot(command_prefix="!", intents=intents)

# 2. Asynchronous CoC Initialization
async def initialize_coc():
    """Handles the async login process and assigns the global client."""
    global coc_client # CRITICAL: This tells Python to update the shared variable
    try:
        # Create the client INSIDE the function so it catches the current loop
        new_client = coc.Client(key_names="Railway Bot")
        await new_client.login(COC_EMAIL, COC_PASSWORD)
        
        # Now assign it to the global variable
        coc_client = new_client
        
        print("✅ CoC Client logged in and global reference updated.")
    except Exception as e:
        print(f"❌ CoC Login Failed: {e}")

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
        # Check if we need to reconnect
        if db_connection is None or not db_connection.is_connected():
            db_connection = connect_db()
            print("✅ Database connected successfully.")
        return db_connection.cursor()
    except Exception as e:
        # This will now show the REAL error in your Railway 'Deploy Logs'
        print(f"❌ DATABASE CONNECTION ERROR: {e}")
        # Raising the error here prevents the 'NoneType' crash in Discord
        raise e