from tokenize import Double
import discord
import os
import requests
import praw
from datetime import timedelta
from discord import app_commands
from discord import Embed
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import random
import time
from PIL import Image, ImageDraw, ImageFont
import mysql.connector
import re
import coc
import asyncio


db_connection = None
cursor = None

TOKEN = os.getenv('DISCORD_TOKEN2')
api_key = os.getenv('COC_api_key')
COC_EMAIL = os.getenv('COC_EMAIL')
COC_PASSWORD = os.getenv('COC_PASSWORD')

# Initialize the CoC Client
# key_names="Railway Bot" helps you identify the key in the dev portal
coc_client = coc.Client(key_names="Railway Bot")

async def initialize_coc():
    try:
        # This one line handles the login and the IP whitelisting automatically
        await coc_client.login(COC_EMAIL, COC_PASSWORD)
        print("Successfully logged into CoC and updated API key for current IP.")
    except coc.InvalidCredentials as e:
        print(f"Failed to login to CoC: {e}")


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix = "!", intents= intents)
print("DB user:", os.getenv("MYSQLUSER"))
print("DB pass exists:", bool(os.getenv("MYSQLPASSWORD")))

# Connect to MySQL Database
def connect_db():
    host     = os.getenv("RAILWAY_TCP_PROXY_DOMAIN", "localhost")
    user     = os.getenv("MYSQLUSER", "root")
    password = os.getenv("MYSQLPASSWORD", os.getenv("MY_SQL_PASSWORD"))
    database = os.getenv("MYSQLDATABASE", os.getenv("MY_SQL_DATABASE2"))
    port     = os.getenv("RAILWAY_TCP_PROXY_PORT", "3306")

    if not all([user, password, database]):
        raise RuntimeError(
            f"Missing DB config: "
            f"MYSQLUSER={user!r}, MYSQLPASSWORD set? {bool(password)}, MYSQLDATABASE={database!r}"
        )

    return mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        autocommit=True,
        auth_plugin="mysql_native_password"
    )

def get_db_connection():
    """Ensures the MySQL connection is active and reconnects if needed."""
    global db_connection, cursor  # ✅ Declare global variables

    if db_connection is None:  # ✅ Ensure db_connection is initialized
        db_connection = connect_db()
        cursor = db_connection.cursor()
        return cursor

    try:
        if not db_connection.is_connected():
            db_connection.reconnect(attempts=3, delay=2)
            cursor = db_connection.cursor()  # ✅ Refresh cursor after reconnecting
    except mysql.connector.Error:
        db_connection = connect_db()  # ✅ Create a new connection if reconnect fails
        cursor = db_connection.cursor()

    return cursor


def format_datetime(dt_str):
    if not dt_str:
        return "N/A"
    try:  #Separates Year Month Day then T Separates date/time, Hours, mins. seconds. 
        dt = datetime.strptime(dt_str, '%Y%m%dT%H%M%S.%fZ').replace(tzinfo=timezone.utc)
        # Convert to Eastern Standard Time (EST)
        est = dt.astimezone(timezone(timedelta(hours=-5)))
        return est.strftime('%Y-%m-%d %H:%M:%S %p EST')
    except ValueError:
        return "N/A"
    
def format_month_day_year(dt_str): #just print month, day and year
    if not dt_str:
        return "N/A"
    try: 
        dt = datetime.strptime(dt_str, '%Y%m%dT%H%M%S.%fZ').replace(tzinfo=timezone.utc)
        # Convert to Eastern Standard Time (EST)
        est = dt.astimezone(timezone(timedelta(hours=-5)))
        return est.strftime('%m-%d-%Y')
    except ValueError:
        return "N/A"
    
def check_coc_clan_tag(clan_tag): 
  #  api_key = 'YOUR_API_KEY'
    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}' 
    headers = { 'Authorization': f'Bearer {api_key}', 'Accept': 'application/json' } 
    response = requests.get(url, headers=headers) 
    if response.status_code == 200: 
        return True # Valid clan tag 
    elif response.status_code == 404: 
        return False

def check_coc_player_tag(player_tag): 
    url = f'https://api.clashofclans.com/v1/players/{player_tag}' 
    headers = { 'Authorization': f'Bearer {api_key}', 'Accept': 'application/json' }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return True
    elif response.status_code == 404:
        return False

import urllib.parse



def get_clan_data(clan_tag: str) -> dict:
    if not api_key:
        raise ValueError("API KEY NOT FOUND")

    tag = clan_tag.strip().upper()
    if not tag.startswith("#"):
        tag = "#" + tag

    encoded_tag = tag.replace("#", "%23")
    url = f'https://api.clashofclans.com/v1/clans/{encoded_tag}'

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        # Default fallback if JSON parsing fails
        error_detail = response.text 
        
        try:
            # Try to parse the JSON error from Clash API
            error_json = response.json()
            
    
            message = error_json.get("message", "No message provided")
            reason = error_json.get("reason", "Unknown reason")
            
            error_detail = f"{reason} - {message}"
            
          
            print(f"\n[!] CLASH API IP ERROR: {message}\n")
            
        except Exception:
            # If response wasn't JSON, just keep the raw text
            pass

        # Raise the error so the bot knows it failed, but now including the IP info
        raise RuntimeError(f"Clash API Error ({response.status_code}): {error_detail}")

    return response.json()

def add_spaces(text):
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', text)

# exceptions.py

class ClanTagError(Exception):
    """Base exception for clan-tag lookup errors."""

class ClanNotSetError(ClanTagError):
    """Raised when no clan tag is set for this server."""
    def __init__(self):
        super().__init__("No clan tag is set for this server. Please set a clan tag using `/setclantag`.")

async def get_capital_raid_data(clan_tag: str) -> dict:
    if not api_key:
        raise ValueError("API KEY NOT FOUND")

    tag = clan_tag.strip().upper()
    if not tag.startswith("#"):
        tag = "#" + tag

    encoded_tag = tag.replace("#", "%23")

    url = f'https://api.clashofclans.com/v1/clans/{encoded_tag}/capitalraidseasons'
   # print(f"Requesting URL: {url}")
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        try:
            reason = response.json().get("reason", response.text)
        except Exception:
            reason = response.text
        raise RuntimeError(f"Clash API Error ({response.status_code}): {reason}")
    return response.json()



# helpers.py

def fetch_clan_from_db(
    cursor,
    guild_id: int,
    provided_tag: str = None
) -> str:
    """
    Returns a normalized clan-tag (including leading '#'), or raises:
      • ClanNotSetError if no tag is in the DB and no provided_tag.
    """
    # 1) If the caller passed in a tag explicitly, normalize & return it
    if provided_tag:
        tag = provided_tag.strip().upper()
        if not tag.startswith("#"):
            tag = "#" + tag
        return tag

    # 2) Otherwise pull from your servers table
    cursor.execute(
        "SELECT clan_tag FROM servers WHERE guild_id = %s",
        (guild_id,)
    )
    row = cursor.fetchone()
    if row and row[0]:
        tag = row[0].strip().upper()
        if not tag.startswith("#"):
            tag = "#" + tag
        return tag

    # 3) Nothing was found
    raise ClanNotSetError()


class PlayerTagError(Exception):
    """Base for our player‐tag lookup errors."""

class PlayerNotLinkedError(PlayerTagError):
    """Raised when a mentioned user has no tag in the DB."""
    def __init__(self, mention: str):
        super().__init__(f"{mention} has not linked a Clash of Clans account.")

class MissingPlayerTagError(PlayerTagError):
    """Raised when neither a user nor a player_tag was provided."""
    def __init__(self):
        super().__init__("Please provide a player tag or mention a linked user.")

def get_player_data(player_tag: str) -> dict:
    if not api_key:
        raise ValueError("API KEY NOT FOUND")

    # Normalize and encode the tag
    tag = player_tag.strip().upper()
    if not tag.startswith("#"):
        tag = "#" + tag

    encoded_tag = tag.replace("#", "%23")

    url = f'https://api.clashofclans.com/v1/players/{encoded_tag}'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        # --- NEW ERROR HANDLING LOGIC ---
        try:
            data = response.json()
        
            message = data.get("message", "No message found") 
            reason = data.get("reason", response.text)
            
    
            print(f"!!! CLASH API ERROR: {message} !!!") 
            
            error_text = f"{reason} - {message}"
        except Exception:
            # Fallback if the response isn't JSON
            error_text = response.text

        raise RuntimeError(f"Clash API Error ({response.status_code}): {error_text}")
    
    return response.json()


def fetch_player_from_DB(cursor,guild_id: int,user: discord.Member = None,provided_tag: str = None) -> str:
    """
    Returns a player_tag string, or raises:
      • PlayerNotLinkedError if `user` was given but not in DB
      • MissingPlayerTagError if neither `user` nor `provided_tag` is set
    """
    if user:
        cursor.execute(
            "SELECT player_tag FROM players "
            "WHERE discord_id = %s AND guild_id = %s",
            (user.id, guild_id)
        )
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]

        raise PlayerNotLinkedError(user.mention)

    if provided_tag:
        return provided_tag

    raise MissingPlayerTagError()


@bot.event
async def on_ready():
    """Fetch clan tags dynamically"""
    await initialize_coc()
    await bot.tree.sync()  # Sync commands globally
    await bot.change_presence(activity=discord.Game(name='Playing with Fire'))
    cursor = get_db_connection()  # Get an active cursor—this ensures reconnect if needed   
    for guild in bot.guilds:
        cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild.id,))
        result = cursor.fetchone()

        if result and result[0]:  # Ensure there's a valid clan tag
            clan_tag = result[0]
            # await guild.me.edit(nick=f"{bot.user.name} | {clan_tag}")  # Update bot's nickname
            # print(f"Updated bot nickname in {guild.name} to: {bot.user.name} | {clan_tag}")

    print(f'Logged in as {bot.user}!')





# cursor.execute("SELECT * FROM servers")
# result = cursor.fetchall()
# print(result)  # Should return stored server data
def get_clan_tag(guild_id):
    """Retrieve the clan tag for a given Discord server."""
    cursor = get_db_connection()  # 
    
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    result = cursor.fetchone()
    
    return result[0] if result and result[0] else None  # ✅ Cleaner return statement
    
@bot.event
async def on_guild_join(guild):
    """Automatically adds the guild_id to the database when bot joins a server."""
    cursor = get_db_connection()  # ✅ Ensure connection is active
    
    cursor.execute(
        "INSERT INTO servers (guild_id, guild_name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE guild_name = VALUES(guild_name)",
        (str(guild.id), guild.name)
    )
    db_connection.commit()

    print(f"Added {guild.name} ({guild.id}) to the database.")



@bot.tree.command(name="help", description="Displays available bot commands")
async def help_command(interaction: discord.Interaction):
    """Sends an embed with categorized commands."""
    embed = discord.Embed(
        title="🛠️ Bot Commands",
        description="Here are the available commands, categorized for easy navigation:",
        color=0x00FF00  # Green color
    )

    # 🛡️ Clans Category
    embed.add_field(
        name="🛡️ Clans",
        value=(
            "`/clanmembers` - View clan members ranked by trophies\n"
            "`/lookupclans` - Search for clans\n"
            "`/lookupmember` - Get Clan info for a specific user\n"
            "`/claninfo` - Retrieve information about the clan\n"
            "`/capitalraid` - Retrieve info on current raid for clan\n"
            "`/previousraids` - Retrieve info about previous seasons for the clan\n"
            "`/warlog` - Retrieve the clan's war log\n"
            "`/currentwar` - Retrieve the clan's current war or CWL war (via tag) info/stats\n"
            "`/cwlschedule` - Retrieve the clan's current CWL and displays rounds\n"
            "`/cwlclansearch` - Search for CWL clan and display CWL roster"
        ),
        inline=False
    )

    # ⚔️ Players Category
    embed.add_field(
        name="⚔️ Players",
        value=(
            "`/playerinfo` - Get player's general information\n"
            "`/playertroops` - Get a player's troop levels\n"
            "`/playerequipments` - Get all levels of a player's equipments\n"
            "`/playerspells` - Get player's spell levels"
        ),
        inline=False
    )

    # 📜 Misc Category
    embed.add_field(
        name="📜 Misc",
        value=(
            "`/announce` - Make an announcement through the bot\n"
            "`/flipcoin` - Flip a coin (heads or tails)\n"
            "`/botstatus` - View tags of the server\n"
        ),
        inline=False
    )
    embed.add_field(
        name="🔧 Settings",
        value =(
            "`/setclantag` - Set the clan tag for this server(This will affect clan commands) \n"
            "`/link` - Link your Clash of Clans account to your Discord account\n"
            "`/unlink` - Unlink your Clash of Clans account from your Discord account\n"

        )
    )

    embed.set_footer(text="Use /command_name to execute a command.")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name ="announce", description ="Make an announcement")
async def announce(interaction: discord.Interaction, message: str):
    await interaction.response.send_message(message)


@bot.tree.command(name="flipcoin", description="Flip coin (heads or tails)")
async def flip(interaction: discord.Interaction):
    integer1 = random.randint(1,2)
    if integer1 == 1:
        await interaction.response.send_message("The coin flips to... Heads!!!")
    elif integer1 == 2:
        await interaction.response.send_message("The coin flips to... Tails!!!")

@bot.tree.command(name="botstatus", description="Get the server status")
async def server_status(interaction: discord.Interaction):
    """Fetches the server's clan tag and all linked Discord usernames."""
    cursor = get_db_connection() 
    
    guild_id = interaction.guild.id  # Get current server ID
    server_count = len(bot.guilds)  # Get the number of servers the bot is in
    user_count = len(bot.users)

    # Fetch the clan tag for the server
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    clan_result = cursor.fetchone()
    clan_tag = clan_result[0] if clan_result else "No clan tag set"

    # Fetch all linked Discord usernames
    cursor.execute("SELECT discord_username, player_tag FROM players WHERE guild_id = %s", (guild_id,))
    player_results = cursor.fetchall()

    if not player_results:
        player_info = "No linked players found."
    else:
        player_info = "\n".join([
            f"@{username} - { player_tag if player_tag else 'Not Linked'}"
            for username, player_tag in player_results
        ])

    # Create embed
    embed = discord.Embed(
        title=f"Server Status for {interaction.guild.name}",
        description=f"**Servers:** {server_count}\n **Users:** {user_count}\n\n **Clan Tag:** {clan_tag}\n\n**Linked Players:**\n{player_info}",
        color=0x3498db
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name='setclantag', description="Set the clan tag for this server")
async def set_clan_tag(interaction: discord.Interaction, new_tag: str):
    global db_connection, cursor
    cursor = get_db_connection()  # Get an active cursor—this ensures reconnect if needed
    global clan_tag

    guild_id = interaction.guild.id  # Get current server ID

    if check_coc_clan_tag(new_tag.replace('#', '%23')):  # Validate the tag
        clan_tag = new_tag.replace('#', '%23')  # Format the clan tag for the API request
       # og_clan_tag = new_tag  # Store the original clan tag for display
        cursor.execute("UPDATE servers SET clan_tag = %s WHERE guild_id = %s", (new_tag, guild_id))
        db_connection.commit()  # Use db_connection.commit() instead of conn.commit()
        
        await interaction.response.send_message(f'Clan tag has been updated to {new_tag} for this server!')
    else:
        await interaction.response.send_message("Not a valid Clan ID")
                  
          
@bot.tree.command(name='link', description="Link your Clash of Clans account to your Discord account")
async def link(interaction: discord.Interaction, player_tag: str):
    """Links a Clash of Clans account to the player's Discord ID and current server."""
    # player_tag = player_tag.replace('#', '%23')
    global db_connection, cursor
    cursor = get_db_connection()  # Get an active cursor—this ensures reconnect if needed
    discord_id = interaction.user.id # Get Discord ID of user
    discord_username = interaction.user.name

    guild_id = interaction.guild.id  # Get current server ID
    guild_name = interaction.guild.name

    # Insert player data, ensuring it's linked to the correct server
    if check_coc_player_tag(player_tag.replace('#', '%23')):  # Validate the player tag
        cursor.execute("""
            INSERT INTO players (discord_id, discord_username, guild_id, guild_name, player_tag)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE player_tag = VALUES(player_tag), discord_username = VALUES(discord_username), guild_name = VALUES(guild_name)
        """, (discord_id, discord_username, guild_id, guild_name, player_tag))

        db_connection.commit()
        await interaction.response.send_message(f"Your Clash of Clans account with tag {player_tag} has been linked to your Discord account in this server.")

    else:
        await interaction.response.send_message(f"Not a valid player tag. Please check and try again.")

@bot.tree.command(name='unlink', description="Unlink your Clash of Clans account from your Discord account")
async def unlink(interaction: discord.Interaction):
    """Removes the player's linked Clash of Clans account from the database."""
    global db_connection, cursor
    cursor = get_db_connection()  
    discord_id = interaction.user.id  # Get Discord ID of user
    guild_id = interaction.guild.id  # Get current server ID

    # Check if the user has a linked account
    cursor.execute("SELECT player_tag FROM players WHERE discord_id = %s AND guild_id = %s", (discord_id, guild_id))
    result = cursor.fetchone()

    if not result:  # If no linked account exists
        await interaction.response.send_message("You don't have a linked Clash of Clans account.")
        return

    # Remove the linked account from the database
    cursor.execute("DELETE FROM players WHERE discord_id = %s AND guild_id = %s", (discord_id, guild_id))
    db_connection.commit()

    await interaction.response.send_message("Your Clash of Clans account has been successfully unlinked.")


#Lists all clan members in clan 
@bot.tree.command(name="clanmembers", description="Get all member info of the clan sorted by League by default") 
@app_commands.describe(ranking= "List by League(default), TH, role, tag")
async def clan_members(interaction: discord.Interaction, ranking: str = "LEAGUES"): 
    # Get the clan tag from the database for the current server
    cursor = get_db_connection()
    guild_id = interaction.guild.id
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    result = cursor.fetchone()
    if not result or not result[0]:
        await interaction.response.send_message("No clan tag is set for this server. Please set a clan tag using /setclantag.")
        return
    
    clan_tag = result[0].replace('#', '%23')  # Format the clan tag for the API request
    await interaction.response.defer()  # Defer the interaction to allow time for processing
    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}/members'
    headers = { 
        'Authorization': f'Bearer {api_key}', 
        'Accept': 'application/json' 
    }
    response = requests.get(url, headers=headers) 
    if response.status_code == 200:
        clan_data = response.json()
        member_list = f"```yaml\n** Members Ranked by {ranking}: ** \n"
        rank = ranking.upper()
        # Sorting members based on the specified ranking criteria
        if rank == "LEAGUES":
            sorted_members = clan_data['items']
        elif rank == "TH":
            sorted_members = sorted(clan_data['items'], key=lambda member: member['townHallLevel'], reverse=True)
        elif rank == "ROLE":
            role_order = {"leader": 1, "coLeader": 2, "admin": 3, "member": 4}
            sorted_members = sorted(clan_data['items'], key=lambda member: role_order.get(member['role'], 5))
        elif rank == "TAG":
            sorted_members = clan_data['items']
        else:
            await interaction.followup.send("Invalid ranking criteria. Please use: leagues, TH, role, or tag.")
            return
       # print(rank)
        # Generating member list
        for member in sorted_members:
            role = member['role']
            if role in ['coLeader', 'leader', 'elder','admin']:
                if role == 'admin':
                    role = 'elder'
                elif role == 'coLeader':
                    role = 'Co-Leader'
                elif role == 'leader':
                    role = 'Leader'
                role = role.upper()

            if rank == "TAG":
                member_info = (
                    f"{member['clanRank']}. {member['name']}, {member['tag']}\n"
                )
            elif rank =="LEAGUES":
               member_info = (
                    f"{member['clanRank']}. {member['name']}, {role}, {member['leagueTier']['name']}\n"
                ) 
            elif rank == "TH" or "ROLE":
                member_info = (
                    f"{member['clanRank']}. {member['name']}, {role}, TH:{member['townHallLevel']}\n"
                )

            if len(member_list) + len(member_info) > 2000 - 3:  # 3 is for the closing ```
                break
            member_list += member_info


        member_list += "```"
        await interaction.followup.send(member_list)
    else: 
        await interaction.response.send_message(f'Error: {response.status_code}, {response.text}')


@bot.tree.command(name ="lookupclans", description = "search for clans")
@app_commands.describe(clanname = "The clan's name", war_frequency = "Filter by war frequency (always)", min_members = "Filter by minimum num. of members", 
max_members = "Filter by maximum num. of members", minclan_level = "Filter by clan Level", limits="Number of clans to return (default 1, max 3)")
async def lookup_clans(interaction: discord.Interaction, clanname: str, war_frequency: str = None, min_members: int = None, 
max_members: int = None, minclan_level: int = None , limits: int=1
):
    if limits <1 or limits > 3:
        limits = 1

    await interaction.response.defer()
    url = f'https://api.clashofclans.com/v1/clans?name={clanname}'
    if war_frequency:
        url+= f'&warFrequency={war_frequency}'
    if min_members:
        url+= f'&minMembers={min_members}'
    if max_members:
        url+= f'&maxMembers={max_members}'
    if minclan_level:
        url+= f'&minClanLevel={minclan_level}' 
    if limits:
        url+=f'&limit={limits}'

    headers = { 'Authorization': f'Bearer {api_key}',
    'Accept': 'application/json'
    }
    response = requests.get(url, headers= headers)
    if response.status_code == 200:
        clan_data = response.json()
      #  description = clan_data['description']
        items = clan_data['items']
        embed = Embed(
            title="Clan Information",
            color=0x3498db,
        )
        for item in items:
            embed.set_thumbnail(url=item['badgeUrls']['small'])
            embed.add_field(name="Name", value=f"{item['name']}", inline=True)
            embed.add_field(name="Tag", value=item['tag'], inline=True)

            embed.add_field(name="Members", value=f":bust_in_silhouette: {item['members']} / 50", inline=False)

            embed.add_field(name="Clan Level", value=item['clanLevel'], inline=True)
            embed.add_field(name="Clan Points", value=item['clanPoints'], inline=True)

            embed.add_field(name="Minimum TownHall Level", value=f"{item['requiredTownhallLevel']}", inline=False)

            embed.add_field(name="Required Trophies", value=f":trophy: {item['requiredTrophies']}", inline=True)
            embed.add_field(name="Required BuilderBase Trophies", value=f":trophy: {item['requiredBuilderBaseTrophies']}", inline=True)
            print(item['isWarLogPublic'])
            if item['isWarLogPublic'] == "True":
                embed.add_field(name="Win/loss ratio", value=f"{item['warWins']} :white_check_mark: / {item['warLosses']} :x:", inline=False)

            embed.add_field(name="Location", value=f":globe_with_meridians: {item['location']['name']}", inline=False)

            await interaction.followup.send(embed=embed)
    elif response.status_code == 404:
        await interaction.followup.send("No information found for the specified clan.")
    else:
        await interaction.followup.send(f"Error retrieving clan info: {response.status_code}, {response.text}")




@bot.tree.command(name="lookupmember", description="Get Information about a clan member")
@app_commands.describe(user="Select a Discord User", username="A clan member's name (optional)")
async def user_info(interaction: discord.Interaction, user: discord.Member = None, username: str = None):
    cursor = get_db_connection()
    guild_id = interaction.guild.id

    try:
        clan_tag = fetch_clan_from_db(cursor, guild_id)
    except ClanNotSetError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)

    normalized_clan_tag = clan_tag.strip().upper()

    try:
        clan_data = get_clan_data(normalized_clan_tag)
    except Exception as e:
        return await interaction.response.send_message(
            f"Error getting clan information: {e}",
            ephemeral=True
        )

    target = None
    timestamp = int(time.time())

    # Case 1: username string provided
    if username:
        for member in clan_data['memberList']:
            if member['name'].lower() == username.lower():
                target = member
                break

    # Case 2: Discord user provided (use linked player tag from DB)
    elif user:
        try:
            linked_tag = fetch_player_from_DB(cursor, guild_id, user, None)
            linked_tag = linked_tag.strip().upper()
            for member in clan_data['memberList']:
                if member['tag'].strip().upper() == linked_tag:
                    target = member
                    break
        except PlayerNotLinkedError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)
        except MissingPlayerTagError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)

    if target:
        role = target['role']
        if role == 'admin':
            role = "Elder"
        elif role == 'coLeader':
            role = "Co-Leader"

        embed = discord.Embed(
            title=f"{target['name']} — {target['tag']}",
            color=discord.Color.green(),
            description=f"Last updated: <t:{timestamp}:R>"
        )
        embed.set_thumbnail(url=target['leagueTier']['iconUrls']['small'])
        embed.add_field(name="TownHall Level", value=str(target['townHallLevel']), inline=True)
        embed.add_field(name="Clan Rank", value=str(target['clanRank']), inline=False)
        embed.add_field(name="Role", value=role, inline=True)
        embed.add_field(name="Trophies", value=f":trophy: {target['trophies']} | {target['leagueTier']['name']}", inline=False)
        embed.add_field(name="Builder Base Trophies", value=f":trophy: {target['builderBaseTrophies']} | {target['builderBaseLeague']['name']}", inline=False)
        embed.add_field(name="Donations", value=f"Given: {target['donations']} | Received: {target['donationsReceived']}", inline=False)

        return await interaction.response.send_message(embed=embed)

    return await interaction.response.send_message(
        f'User "{username or user.display_name}" not found in the clan.',
        ephemeral=True
    )




@bot.tree.command(name="claninfo", description="Retrieve information about the clan")
async def clanInfo(interaction: discord.Interaction):
    # 1) FAST-FAIL + fetch tag from DB (or provided_tag)
    cursor = get_db_connection()
    guild_id = interaction.guild.id
    try:
        tag = fetch_clan_from_db(cursor, guild_id)
    except ClanNotSetError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)

    normalized_tag = tag.strip().upper()

    # 2) Fetch clan data (synchronous)
    try:
        clan_data = get_clan_data(normalized_tag)
    except Exception as e:
        return await interaction.response.send_message(
            f"Error getting clan information: {e}",
            ephemeral=True
        )

    # 3) Build embed
    description = clan_data['description']
    timestamp   = int(time.time() // 60 * 60)  # round to minute

    embed = Embed(
        title="Clan Information",
        description=f"Last updated: <t:{timestamp}:R>",
        color=0x3498db
    )
    embed.set_thumbnail(url=clan_data['badgeUrls']['small'])
    embed.add_field(name="Name", value=clan_data['name'], inline=True)
    embed.add_field(name="Tag", value=clan_data['tag'], inline=True)

    embed.add_field(name="Members",value=f":bust_in_silhouette: {clan_data['members']} / 50",inline=False)


    embed.add_field(name="Level", value=clan_data['clanLevel'], inline=True)
    embed.add_field(name="War Frequency", value=add_spaces(clan_data['warFrequency']), inline=True)

    embed.add_field(name="Description", value=description, inline=False)
    embed.add_field(
        name="Min. TH Level",
        value=str(clan_data['requiredTownhallLevel']),
        inline=True
    )
    embed.add_field(
        name="Req. Trophies",
        value=f":trophy: {clan_data['requiredTrophies']}",
        inline=True
    )
    embed.add_field(
        name="Req. Builder Base Trophies",
        value=f":trophy: {clan_data['requiredBuilderBaseTrophies']}",
        inline=True
    )
    if clan_data['isWarLogPublic']:
        embed.add_field(
            name="War Win/Draw/Loss Record",
            value=f"{clan_data['warWins']}  / {clan_data['warTies']} / {clan_data['warLosses']} ",
            inline=True
        )
        embed.add_field(name = "War Streak", value=str(clan_data['warWinStreak']), inline=True)

    embed.add_field(name ="CWL League", value=clan_data['warLeague']['name'], inline=False)
    embed.add_field(name ="Clan Capital League", value=clan_data['capitalLeague']['name'], inline=True)
    embed.add_field(
        name="Location",
        value=f":globe_with_meridians: {clan_data['location']['name']}",
        inline=False
    )
    embed.set_footer(text=f"Requested by {interaction.user.name}")

    # 4) Send a single response – no defer(), no followup
    await interaction.response.send_message(embed=embed)




@bot.tree.command(name="capitalraid", description="Retrieve information about info on current raid for clan")
async def capitalraid(interaction: discord.Interaction):
    cursor = get_db_connection()
    guild_id = interaction.guild.id
    try:
        tag = fetch_clan_from_db(cursor, guild_id)
    except ClanNotSetError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)

    normalized_tag = tag.strip().upper()

    # 2) Fetch clan data (synchronous)
    try:
        raid_data = await get_capital_raid_data(normalized_tag)
    except Exception as e:
        return await interaction.response.send_message(
            f"Error getting clan information: {e}",
            ephemeral=True
        )
        # timestamp = int(time.time())

    seasons = raid_data.get('items', [])
    
    if not seasons:
        await interaction.followup.send("No capital raid seasons found for the specified clan.")
        return
    await interaction.response.defer()

    raid_info_list = []
    raid_info = None
    for i, entry in enumerate(seasons[:1]):  # Limit to the first season
        state = entry.get('state','N/A' )
        start_time = format_datetime(entry.get('startTime', 'N/A'))
        end_time = format_datetime(entry.get('endTime', 'N/A'))
        capitalTotalLoot = entry.get('capitalTotalLoot')
        defensive_reward = entry.get('defensiveReward')
        offensive_reward = entry.get('offensiveReward')
        total_attacks = entry.get('totalAttacks')
        reward =0
        

        members = entry.get('members', [])
        attacks = 0
        #  print(f"Members: {members}")
        member_loot_stats = {}
        member_attacks = {}
        for member in members:
            member_name = member.get('name', 'N/A')
            #  print(f"Attacker info: {attacker}")  # Debugging print statement
            total_loot = member.get('capitalResourcesLooted', 0)
            attacks = member.get('attacks', 0)

            if member_name in member_loot_stats:
                member_loot_stats[member_name] += total_loot
            else:
                member_loot_stats[member_name] = total_loot

            if member_name in member_attacks:
                member_attacks[member_name] += attacks
            else:
                member_attacks[member_name] = attacks


        #  print(f"Member loot stats: {member_loot_stats}")  # Debugging print statement

        sorted_member_stats = sorted(member_loot_stats.items(), key=lambda x: x[1], reverse = True)

        numbered_member_stats = "\n".join( 
            [f"{idx + 1}. {member}: {loot} loot, {member_attacks.get(member, 0)} attack(s)" 
            for idx, (member, loot) in enumerate(sorted_member_stats)] 
            )
        #made use of https://www.reddit.com/r/ClashOfClans/comments/yox6dd/how_offensive_raid_medals_are_precisely/ for calcs 
        if state == 'ongoing':
            attack_log = entry.get('attackLog', [])
            for hi in attack_log:
                districts = hi.get('districts',[])
                for crib in districts:
                    destruction = crib.get('destructionPercent')
                    capital = crib.get('name')
                    level = crib.get('districtHallLevel')
                    if destruction == 100:
                        if capital == "Capital Peak":
                            if level == 10:
                                reward+=1450
                            elif level ==9:
                                reward+=1375
                            elif level ==8:
                                reward+=1260
                            elif level ==7:
                                reward+=1240
                            elif level ==6:
                                reward+=1115
                            elif level ==5:
                                reward+=810
                            elif level ==4:
                                reward+=585
                            elif level ==3:
                                reward+=360
                            elif level ==2:
                                reward+=180
                        else:
                            if level == 5:
                                reward += 460
                            if level == 4:
                                reward += 405
                            if level == 3:
                                reward += 350
                            if level == 2:
                                reward += 225
                            if level == 1:
                                reward += 135   

            raid_info = (
            f"```yaml\n"
            f"Status: {state}\n"
            f"Start Time: {start_time}\n"
            f"End Time: {end_time}\n"
            f"Estimated Earning Medals: {round(reward):,} | Total Loot: {capitalTotalLoot:,}\n"
            f"Member Loot Stats:\n{numbered_member_stats}\n"
            f"```\n"
        )
        #and defensive_reward !=0
        elif state == 'ended' and offensive_reward!=0:
            offensive_reward = offensive_reward * 6.0
            total_reward = offensive_reward + defensive_reward
            raid_info = (
                f"```yaml\n"
                f"Status: {state}\n"
                f"Start Time: {start_time}\n"
                f"End Time: {end_time}\n"
                f"Raid Medals Earned: {round(total_reward):,} | Total Loot Obtained: {capitalTotalLoot:,}\n"
                f"Member Loot Stats:\n{numbered_member_stats}\n"
                f"```\n"
            )
    
    raid_info_list.append(raid_info)
    
    chunk_size = 2000
    raid_info_message = "\n".join(raid_info_list)
    for i in range(0, len(raid_info_message), chunk_size):
        await interaction.followup.send(raid_info_message[i:i+chunk_size])


        
@bot.tree.command(name="previousraids", description="Retrieve information about capital raid seasons for the clan")
@app_commands.describe(limit="The number of raids to retrieve (default:2, max:5)")
async def previous_raids(interaction: discord.Interaction, limit: int = 2):
    cursor = get_db_connection()
    guild_id = interaction.guild.id
    try:
        tag = fetch_clan_from_db(cursor, guild_id)
    except ClanNotSetError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)

    normalized_tag = tag.strip().upper()

    # 2) Fetch clan data (synchronous)
    try:
        raid_data = await get_capital_raid_data(normalized_tag)
    except Exception as e:
        return await interaction.response.send_message(
            f"Error getting clan information: {e}",
            ephemeral=True
        )
    seasons = raid_data.get('items', [])
    await interaction.response.defer()

    
    if not seasons:
        await interaction.followup.send("No capital raid seasons found for the specified clan.")
        return

    limit = max(2, min(limit, 5))  # Limit the number of raids retrieved
    for i, entry in enumerate(seasons[:limit]):  # Limit to the first few seasons
        state = entry.get('state', 'N/A')
        start_time = format_month_day_year(entry.get('startTime', 'N/A'))
        end_time = format_month_day_year(entry.get('endTime', 'N/A'))
        capital_total_loot = entry.get('capitalTotalLoot', 'N/A')
        attacks = entry.get('totalAttacks', 'N/A')
        defensive_reward = entry.get('defensiveReward', 0)
        offensive_reward = entry.get('offensiveReward', 0) * 6.0
        total_reward = offensive_reward + defensive_reward
        districts_destroyed = entry.get('enemyDistrictsDestroyed', 'N/A')
        total_attacks = entry.get('totalAttacks')

        
        if state == 'ongoing':
            colors=0xffff00 
        if state == 'ended':
            colors= 0x1abc9c 
        # Create embed
        embed = Embed(
            title=f"Raid #{i + 1}:",
            color=colors  # Light green color
        )
        #   embed.set_thumbnail(url=)
        embed.add_field(name="Status", value=state, inline=False)
        embed.add_field(name="Start Time", value=start_time, inline=True)
        embed.add_field(name="End Time", value=end_time, inline=True)
        embed.add_field(name="Capital Loot Obtained", value=f"{capital_total_loot:,}", inline=False)
        embed.add_field(name="Total Attacks", value=f"{attacks:,}", inline=True)
        embed.add_field(name="Districts Destroyed", value=districts_destroyed, inline=True)
        if total_reward ==0:
            embed.add_field(name="Raid Medals Earned", value="Still Calculating...", inline=False)
        else:
            embed.add_field(name="Raid Medals Earned", value=f"{round(total_reward):,}", inline=False)
        
        # Send the embed for each raid
        await interaction.followup.send(embed=embed)


@bot.tree.command(name="warlog", description="Retrieve the war log for the specified clan")
@app_commands.describe(limit="The number of wars to retrieve (default 1, max 8)")
async def warLog(interaction: discord.Interaction, limit: int = 1):
    cursor = get_db_connection()
    guild_id = interaction.guild.id
    try:
        tag = fetch_clan_from_db(cursor, guild_id)
    except ClanNotSetError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)
    await interaction.response.defer()  
    if not api_key:
        raise ValueError("API KEY NOT FOUND")
    normalized_tag = tag.replace("#", "%23")
    
    url = f'https://api.clashofclans.com/v1/clans/{normalized_tag}/warlog'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        war_log = response.json()
        war_entries = war_log.get('items', [])
        timestamp = int(time.time())

        if not war_entries:
            await interaction.followup.send("No war log entries found for the specified clan.")
            return

        # Ensure the limit is constrained between 1 and 8
        limit = max(1, min(limit, 8))

        # Take the most recent `limit` wars (assuming they are listed first)
        war_entries = war_entries[:limit]

        # Generate embed messages for each war entry
        for i, entry in enumerate(war_entries):
            attacks_per_member = entry['attacksPerMember']

            our_tag = entry['clan']['tag']
            clan_stars = entry['clan']['stars']
            clan_destruction = round(entry['clan']['destructionPercentage'],2)


            opponent_name = entry['opponent'].get('name', 'IN CWL')
            opponent_tag = entry['opponent'].get('tag', '')
            opponent_stars = entry['opponent']['stars']
            opp_destruction = round(entry['opponent']['destructionPercentage'],2)
            
            # Determine embed color based on the result
            if entry['result'] == "win":
                embed_color = 0x00ff00  # Green for win
            elif entry['result'] == "lose":
                embed_color = 0xff0000  # Red for loss
            elif entry['result'] == "tie":
                embed_color = 0xffff00  # Yellow for tie
            else:
                embed_color = 0x808080  # Gray for unknown results
            result = f"Result: :first_place: {entry['result'].capitalize()}" if entry['result'] =='win' else f"Result: :second_place: {entry['result'].capitalize()}"
            embed = Embed(
                title=f"{entry['clan']['name']} vs {opponent_name}",
                    description=f"{result}\n Last Updated: <t:{timestamp}:R>",
                color=embed_color  # Apply dynamic color
            )
            
        

            if attacks_per_member == 2:  # Regular War
                embed.add_field(name="Clan Tag", value=our_tag, inline=True)
                embed.add_field(name="Clan Stars", value=f":star: {clan_stars}", inline=True)
                embed.add_field(name="Clan Destruction", value=f":fire: {clan_destruction}%", inline=True)

                embed.add_field(name="Opponent Tag", value=opponent_tag, inline=True)
                embed.add_field(name="Opponent Stars", value=f":star: {opponent_stars}", inline=True)
                embed.add_field(name="Opponent Destruction", value=f":fire: {opp_destruction}%", inline=True)

                embed.add_field(name="Team Size", value=f":bust_in_silhouette: {entry['teamSize']}", inline=True)
                embed.add_field(name="Exp Gained", value=entry['clan']['expEarned'], inline=True)
                embed.add_field(name="Clan Level", value=entry['clan'].get('clanLevel', 'N/A'), inline=True)

            elif attacks_per_member == 1:  # CWL Log
                attacks_per_member*=7
                embed.add_field(name="Clan Stars", value=f":star: {entry['clan']['stars']}", inline=True)
                embed.add_field(name="Clan Destruction", value=f":fire: {clan_destruction}%", inline=True)
                embed.add_field(name="Team Size", value=f":bust_in_silhouette: {entry['teamSize']}", inline=True)
                embed.add_field(name="Attacks", value=f"{entry['clan']['attacks']} / {attacks_per_member}", inline=False)


            embed.add_field(name="End Date", value=format_month_day_year(entry.get('endTime', 'N/A')), inline=False)
            embed.set_footer(text="Clash of Clans War Log")

            # Send the embed to the user
            await interaction.followup.send(embed=embed)

    elif response.status_code == 404:
        await interaction.followup.send("No war log found for the specified clan.")
    elif response.status_code == 403:
        await interaction.followup.send("Clan's war log is private. Cannot display war log.")
    else:
        await interaction.followup.send(f"Error retrieving war log: {response.status_code}, {response.text}")



@bot.tree.command(
    name="currentwar",
    description="Get info or stats for current war (normal or CWL)"
)
@app_commands.describe(
    wartag="(Optional) CWL war tag (e.g. #8LC8U2VP2). If omitted, shows your clan’s current normal war.",
    mode="Choose 'info' for general war info or 'stats' for player stats"
)
async def currentwar(
    interaction: discord.Interaction,
    wartag: str = None,
    mode: str = "info"   # default to general info
):
    cursor = get_db_connection()
    guild_id = interaction.guild.id
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    row = cursor.fetchone()

    if not row or not row[0]:
        return await interaction.response.send_message(
            "No clan tag is set for this server. Use `/setclantag` first.",
            ephemeral=True
        )

    db_tag = row[0].strip().lstrip("#").upper()
    await interaction.response.defer()

    if not api_key:
        raise ValueError("API KEY NOT FOUND")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    # Choose endpoint
    if wartag:
        wt = wartag.strip().lstrip("#").upper()
        url = f"https://api.clashofclans.com/v1/clanwarleagues/wars/%23{wt}"
        is_cwl = True
        source = "CWL"
    else:
        url = f"https://api.clashofclans.com/v1/clans/%23{db_tag}/currentwar"
        is_cwl = False
        source = "Normal"

    resp = requests.get(url, headers=headers)
    if resp.status_code == 403:
        return await interaction.followup.send(
            "War data is private for this clan. Cannot display current war."
        )
    if resp.status_code != 200:
        return await interaction.followup.send(
            f"Error fetching war: {resp.status_code} – {resp.text}"
        )

    war_data = resp.json()

    # Determine which side is our clan
    def normalize(t: str) -> str: return t.strip().lstrip("#").upper()
    clanA, clanB = war_data.get("clan", {}), war_data.get("opponent", {})
    if is_cwl:
        if normalize(clanA.get("tag","")) == db_tag:
            our_block, opp_block = clanA, clanB
        else:
            our_block, opp_block = clanB, clanA
    else:
        our_block, opp_block = clanA, clanB

    # Mode: General Info (embed)
    if mode.lower() == "info":
        state = war_data.get("state", "Unknown")
        start_time = format_datetime(war_data.get("startTime", "N/A"))
        end_time   = format_datetime(war_data.get("endTime", "N/A"))
        clan_stars = our_block.get("stars", 0)
        opp_stars  = opp_block.get("stars", 0)
        clan_destr = round(our_block.get("destructionPercentage", 0), 2)
        opp_destr  = round(opp_block.get("destructionPercentage", 0), 2)

        embed = Embed(
            title=f"{our_block.get('name','?')} vs {opp_block.get('name','?')}",
            description=f"{source} War — State: :crossed_swords: {state.capitalize()}",
            color=0x00ff00 if clan_stars > opp_stars else 0xff0000 if clan_stars < opp_stars else 0xffff00
        )
        embed.add_field(name="Start Time", value=start_time, inline=True)
        embed.add_field(name="End Time", value=end_time, inline=True)
        embed.add_field(name="War Size", value=f":bust_in_silhouette: {war_data.get('teamSize','?')}", inline=False)
        embed.add_field(name="Clan Stars", value=f":star: {clan_stars}", inline=True)
        embed.add_field(name="Clan Destruction", value=f":fire: {clan_destr}%", inline=True)
        embed.add_field(name="Opponent Stars", value=f":star: {opp_stars}", inline=True)
        embed.add_field(name="Opponent Destruction", value=f":fire: {opp_destr}%", inline=True)
        embed.set_footer(text="Clash of Clans War Information")

        return await interaction.followup.send(embed=embed)

    # Mode: Player Stats (YAML style)
    else:
        max_attacks = 1 if is_cwl else 2
        members = our_block.get("members", [])

        def collect_stats(members):
            attacked, unattacked = [], []
            for m in members:
                name = m.get("name")
                th   = m.get("townhallLevel") or m.get("townHallLevel")
                atks = m.get("attacks", [])
                cnt  = len(atks)
                stars = sum(a.get("stars", 0) for a in atks)
                pct   = sum(a.get("destructionPercentage", 0) for a in atks)
                entry = {"name": name, "th": th, "stars": stars, "pct": pct, "att": cnt}
                (attacked if cnt > 0 else unattacked).append(entry)

            attacked.sort(key=lambda e:(e["stars"], e["pct"]), reverse=True)
            unattacked.sort(key=lambda e:(e["th"], e["name"]))
            return attacked, unattacked

        with_attacks, without_attacks = collect_stats(members)

        lines = ["```yaml"]
        lines.append(f"{source} War Stats — {our_block.get('name','Your Clan')}")
        lines.append(f"State: {war_data.get('state','Unknown')}")
        if st := war_data.get("startTime"): lines.append(f"Start: {format_datetime(st)}")
        if et := war_data.get("endTime"):   lines.append(f"End:   {format_datetime(et)}")
        lines.append("")
        lines.append("✅ Attacked")
        for i, e in enumerate(with_attacks, start=1):
            lines.append(f"{i}. {e['name']}: Stars {e['stars']}, Destr {e['pct']}%, Attacks {e['att']}/{max_attacks}")
        lines.append("")
        lines.append("❌ Not Attacked")
        for i, e in enumerate(without_attacks, start=1):
            lines.append(f"{i}. {e['name']}: TH {e['th']}, Attacks {e['att']}/{max_attacks}")
        lines.append("```")

        return await interaction.followup.send("\n".join(lines))



# @bot.tree.command(name="currentwarstats",
#     description="Receive player stats for your current war or a CWL war by warTag"
# )
# @app_commands.describe(
#     wartag="(Optional) CWL war tag (e.g. #8LC8U2VP2). If omitted, shows your clan’s current normal war."
# )
# async def warInfo(
#     interaction: discord.Interaction,
#     wartag: str = None
# ):
#     # 1) Fetch your clan_tag from the database BEFORE deferring
#     cursor   = get_db_connection()
#     guild_id = interaction.guild.id
#     cursor.execute(
#         "SELECT clan_tag FROM servers WHERE guild_id = %s",
#         (guild_id,)
#     )
#     row = cursor.fetchone()
#     if not row or not row[0]:
#         # ephemeral reply if no tag is set
#         return await interaction.response.send_message(
#             "No clan tag is set for this server. Use `/setclantag` first.",
#             ephemeral=True
#         )

#     # 2) Normalize your saved tag
#     db_tag = row[0].strip().lstrip("#").upper()

#     # 3) Now defer once for the long work
#     await interaction.response.defer()

#     # 4) Prepare headers
#     headers = {
#         "Authorization": f"Bearer {api_key}",
#         "Accept":        "application/json"
#     }

#     # 5) Choose endpoint based on wartag vs. normal war
#     if wartag:
#         wt   = wartag.strip().lstrip("#").upper()
#         url  = f"https://api.clashofclans.com/v1/clanwarleagues/wars/%23{wt}"
#         is_cwl = True
#         source = "CWL"
#     else:
#         url     = f"https://api.clashofclans.com/v1/clans/%23{db_tag}/currentwar"
#         is_cwl  = False
#         source  = "Normal"

#     # 6) Fetch war data
#     resp = requests.get(url, headers=headers)
#     if resp.status_code == 404:
#         return await interaction.followup.send(
#             "No CWL war found with that tag." if wartag
#             else "Your clan is not in a war right now."
#         )
#     if resp.status_code != 200:
#         return await interaction.followup.send(
#             f"Error fetching war: {resp.status_code} – {resp.text}"
#         )

#     war_data = resp.json()

#     # 7) Normalize helper for tags
#     def normalize(t: str) -> str:
#         return t.strip().lstrip("#").upper()

#     # 8) Determine which side is your clan
#     clanA = war_data.get("clan", {})
#     clanB = war_data.get("opponent", {})
#     if is_cwl:
#         # compare both sides to your DB tag
#         if normalize(clanA.get("tag","")) == db_tag:
#             our_block, opp_block = clanA, clanB
#         else:
#             our_block, opp_block = clanB, clanA
#     else:
#         # normal war: "clan" is always your clan
#         our_block, opp_block = clanA, clanB

#     # 9) Set max attacks (1 for CWL, 2 for normal wars)
#     max_attacks = 1 if is_cwl else 2

#     # 10) Collect and sort stats
#     def collect_stats(members):
#         attacked, unattacked = [], []
#         for m in members:
#             name = m.get("name")
#             th   = m.get("townhallLevel") or m.get("townHallLevel")
#             atks = m.get("attacks", [])
#             cnt  = len(atks)
#             stars = sum(a.get("stars", 0) for a in atks)
#             pct   = sum(a.get("destructionPercentage", 0) for a in atks)
#             entry = {"name": name, "th": th, "stars": stars, "pct": pct, "att": cnt}
#             (attacked if cnt > 0 else unattacked).append(entry)

#         attacked.sort(key=lambda e:(e["stars"], e["pct"]), reverse=True)
#         unattacked.sort(key=lambda e:(e["th"], e["name"]))
#         return attacked, unattacked

#     members = our_block.get("members", [])
#     with_attacks, without_attacks = collect_stats(members)

#     # 11) Build the YAML‐style lines
#     lines = ["```yaml"]
#     lines.append(f"**{source} War Stats — {our_block.get('name','Your Clan')}**")
#     lines.append(f"State: {war_data.get('state','Unknown')}")
#     if st := war_data.get("startTime"):
#         lines.append(f"Start: {format_datetime(st)}")
#     if et := war_data.get("endTime"):
#         lines.append(f"End:   {format_datetime(et)}")
#     lines.append("")    
#     lines.append("✅ Attacked")
#     for i, e in enumerate(with_attacks, start=1):
#         lines.append(
#             f"{i}. {e['name']}: Stars {e['stars']}, "
#             f"Destr {e['pct']}%, Attacks {e['att']}/{max_attacks}"
#         )
#     lines.append("")    
#     lines.append("❌ Not Attacked")
#     for i, e in enumerate(without_attacks, start=1):
#         lines.append(
#             f"{i}. {e['name']}: TH {e['th']}, Attacks {e['att']}/{max_attacks}"
#         )
#     lines.append("```")

#     await interaction.followup.send("\n".join(lines))
        
@bot.tree.command(name="cwlschedule", description="Receive information about the current CWL Schedule")
async def warInfo(interaction: discord.Interaction):
    DEFAULT_CLAN_TAG = "#2JL28OGJJ"


    cursor   = get_db_connection()
    guild_id = interaction.guild.id
    cursor.execute(
        "SELECT clan_tag FROM servers WHERE guild_id = %s",
        (guild_id,)
    )
    row = cursor.fetchone()
    # if not row or not row[0]:
    #     return await interaction.response.send_message(
    #         "No clan tag is set for this server. Use /setclantag first.",
    #         ephemeral=True
    #     )
    raw_tag = row[0] if row and row[0] else DEFAULT_CLAN_TAG
    enc_tag = raw_tag.replace("#", "%23")

    # 2) Defer for API time
    await interaction.response.defer()

    # 3) Normalizer helper
    def normalize(t: str) -> str:
        return t.strip().lstrip("#").upper()

    my_norm = normalize(raw_tag)

    # 4) Fetch the CWL leaguegroup
    url     = f"https://api.clashofclans.com/v1/clans/{enc_tag}/currentwar/leaguegroup"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept":        "application/json"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 404:
        return await interaction.followup.send(
            "This clan is not participating in CWL right now."
        )
    if response.status_code != 200:
        return await interaction.followup.send(
            f"Error fetching CWL: {response.status_code} – {response.text}"
        )

    data   = response.json()
    state  = data.get("state",  "Unknown")
    season = data.get("season", "Unknown")
    clans  = data.get("clans",  [])
    rounds = data.get("rounds", [])

    # 5) Build header & participating clans list
    lines = [
        f"**CWL Season {season}**  -  State: {state}",
        "",
        "Participating Clans:"
    ]
    for i, c in enumerate(clans, start=1):
        lines.append(
            f"{i}. {c['name']} ({c['tag']}) – Level {c['clanLevel']}"
        )

    lines.append("") 
    lines.append("Round Schedule:")

    # 6) Cache war detail lookups
    war_cache = {}

    # 7) For each round, find your clan's warTag, then print the opponent name
    for idx, rnd in enumerate(rounds, start=1):
        clan_wt       = None
        opponent_name = None

        for wt in rnd.get("warTags", []):
            if not wt or wt == "#0":
                continue

            # fetch & cache the war detail
            if wt not in war_cache:
                wt_enc = wt.replace("#", "%23")
                wresp  = requests.get(
                    f"https://api.clashofclans.com/v1/clanwarleagues/wars/{wt_enc}",
                    headers=headers
                )
                if wresp.status_code == 200:
                    war_cache[wt] = wresp.json()
                else:
                    war_cache[wt] = None

            wdata = war_cache[wt]
            if not wdata:
                continue

            tagA = wdata["clan"]["tag"]
            tagB = wdata["opponent"]["tag"]
            # match your clan on either side
            if normalize(tagA) == my_norm:
                clan_wt       = wt
                opponent_name = wdata["opponent"]["name"]
                break
            if normalize(tagB) == my_norm:
                clan_wt       = wt
                opponent_name = wdata["clan"]["name"]
                break

        # 8) Append one line: opponent + (warTag) or fallback
        if clan_wt:
            lines.append(f"Round {idx}: {opponent_name} (War Tag: {clan_wt})")
        else:
            lines.append(f"Round {idx}: Not yet scheduled")

    # 9) Wrap in a YAML code block and send
    text = "```yaml\n" + "\n".join(lines) + "\n```"
    await interaction.followup.send(text)


# @bot.tree.command(name="cwlspecificwars", description="Receive general information about current war")
# @app_commands.describe(war_tag = "The specific war tag for individual CWL War")
# async def warInfo(interaction: discord.Interaction, war_tag: str):
#     cursor = get_db_connection()
#     guild_id = interaction.guild.id
#     cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
#     result = cursor.fetchone()

#     if not result or not result[0]:
#         await interaction.response.send_message("No clan tag is set for this server. Please set a clan tag using /setclantag.")
#         return
    
#     clan_tag = result[0].replace('#', '%23')  # Format the clan tag for the API request
#     await interaction.response.defer()  # Defer the interaction to allow time for processing

#     if not api_key:
#         raise ValueError("API KEY NOT FOUND")
#     war_tag = war_tag.replace('#', '%23')  # Format the war tag for the API request

#     url= f'https://api.clashofclans.com/v1/clanwarleagues/wars/{war_tag}'
#     headers = {
#         'Authorization': f'Bearer {api_key}',
#         'Accept': 'application/json'
#     }
#     response = requests.get(url, headers=headers)

#     if response.status_code == 200:
#         war_data = response.json()
#         state = war_data['state']
#         timestamp = int(time.time() // 60 * 60)  # Convert to seconds for the footer

#         if state == 'inWar' or state == 'warEnded':
#             start_time = format_datetime(war_data.get('startTime', 'N/A'))
#             end_time = format_datetime(war_data.get('endTime', 'N/A'))
#             num_of_attacks = war_data['teamSize'] 
#             clan_stars = war_data['clan']['stars']
#             opp_stars = war_data['opponent']['stars']

#             cwl_clan_tag = war_data['clan']['tag']
#             cwl_opp_tag = war_data['opponent']['tag']

#             destruction_percentage = round(war_data['clan']['destructionPercentage'], 2)
#             opp_destruction_percentage = round(war_data['opponent']['destructionPercentage'], 2)

#             # Create the embed
#             embed = Embed(
#                 title=f"{war_data['clan']['name']} vs {war_data['opponent']['name']}",
#                 description=f"State: {war_data['state'].capitalize()}\n Last Updated: <t:{timestamp}:R>",
#                 color=0x00ff00 if  cwl_clan_tag == clan_tag and clan_stars > opp_stars 
#                 else 0x00ff00 if  cwl_opp_tag == clan_tag and clan_stars < opp_stars 
#                 else 0xFFFF00 if  cwl_opp_tag == clan_tag and clan_stars == opp_stars 
#                 else 0x808080  # Green for winning  wars, red is for losing  wars, yellow for ties,  Gray for unknown results
#             )
#             if cwl_clan_tag == clan_tag: 
#                 embed.set_thumbnail(url=war_data['clan']['badgeUrls']['small'])
#             elif cwl_opp_tag == clan_tag:
#                 embed.set_thumbnail(url= war_data['opponent']['badgeUrls']['small'])

#             embed.add_field(name="Start Time", value=start_time, inline=True)
#             embed.add_field(name="End Time", value=end_time, inline=True)

#             embed.add_field(name="War Size", value=war_data['teamSize'], inline=False)

#             embed.add_field(name="Clan Tag", value=war_data['clan']['tag'], inline=True)
#             if {war_data['clan']['attacks']} == num_of_attacks:
#                 embed.add_field(name="Clan Stars", value=f":star: {clan_stars} (Attacks: {war_data['clan']['attacks']}/{num_of_attacks} :white_check_mark:)", inline=True)
#             else:
#                 embed.add_field(name="Clan Stars", value=f":star: {clan_stars} (Attacks: {war_data['clan']['attacks']}/{num_of_attacks})", inline=True)

#             if destruction_percentage == 100:
#                 embed.add_field(name="Clan Destruction", value=f":fire: {destruction_percentage}%", inline=True)
#             else:
#                 embed.add_field(name="Clan Destruction", value=f":fire: {destruction_percentage}%", inline=True)

#             embed.add_field(name="Opponent Tag", value=war_data['opponent']['tag'], inline=True)
#             embed.add_field(name="Opponent Stars", value=f":star: {opp_stars} (Attacks: {war_data['opponent']['attacks']}/{num_of_attacks})", inline=True)
#             embed.add_field(name="Opponent Destruction", value=f":fire: {opp_destruction_percentage}%", inline=True)

#             embed.set_footer(text="Clash of Clans Current War Information")

#             await interaction.followup.send(embed=embed)

#         elif state == 'preparation':
#             start_time = format_datetime(war_data.get('startTime', 'N/A'))
#             end_time = format_datetime(war_data.get('endTime', 'N/A'))
#             preparation_time = format_datetime(war_data.get('preparationStartTime', 'N/A'))

#             # Create the embed
#             embed = Embed(
#                 title="War Preparation",
#                 description=f"Current War is in preparation state.\n Last Updated: <t:{timestamp}:R>",
#                 color=0xFFFF00  # Yellow for preparation
#             )
#             embed.add_field(name="Preparation Start Time", value=preparation_time, inline=True)
#             embed.add_field(name="Start Time", value=start_time, inline=True)
#             embed.add_field(name="End Time", value=end_time, inline=True)
#             embed.add_field(name="War Size", value=war_data['teamSize'], inline=True)
#             embed.add_field(name="Clan", value=f"{war_data['clan']['name']} (Tag: {war_data['clan']['tag']})", inline=False)
#             embed.add_field(name="Opponent", value=f"{war_data['opponent']['name']} (Tag: {war_data['opponent']['tag']})", inline=False)
#             embed.set_footer(text="Clash of Clans War Preparation Info")

#             await interaction.followup.send(embed=embed)

#         elif state == 'notInWar':
#             # Create the embed for not in war state
#             embed = Embed(
#                 title="No Active War",
#                 description=f"The clan is currently not in war.\n Last Updated: <t:{timestamp}:R>",
#                 color=0xFF2C2C  # Blue for no war
#             )
#             embed.add_field(name="State", value=war_data['state'], inline=False)
#             embed.set_footer(text="Clash of Clans Current War Info")

#             await interaction.followup.send(embed=embed)

#     elif response.status_code == 404:
#         await interaction.followup.send("No current war found for the specified clan.")
#     else:
#         await interaction.followup.send(f"Error retrieving current war info: {response.status_code}, {response.text}")


@bot.tree.command(name= "cwlclansearch",description = "Search CWL clans by name or tag")
@app_commands.describe(nameortag = "Clan name (e.g. MyClan) or tag (e.g. #2PLGJ8PQJ)")
async def CWL_clan_search(interaction: discord.Interaction, nameortag: str):
    # 1) fetch saved clan tag
    DEFAULT_CLAN_TAG = "#2JL28OGJJ"
    cursor   = get_db_connection()
    guild_id = interaction.guild.id
    cursor.execute(
        "SELECT clan_tag FROM servers WHERE guild_id = %s",
        (guild_id,)
    )
    row = cursor.fetchone()
    # if not row or not row[0]:
    #     return await interaction.response.send_message(
    #         "No clan tag set for this server. Use `/setclantag` first.",
    #         ephemeral=True
    #     )

    raw_tag = row[0] if row and row[0] else DEFAULT_CLAN_TAG
    enc_tag = raw_tag.replace("#", "%23")

    # 2) detect name vs tag
    query  = nameortag.strip()
    is_tag = query.startswith("#") or re.fullmatch(r"[0-9A-Z]+", query.upper())
    
    if is_tag:
        search_tag = query.upper().lstrip("#")
    else:
        search_name = query.lower()

    await interaction.response.defer()

    # 3) fetch CWL state
    headers    = {
        "Authorization": f"Bearer {api_key}",
        "Accept":        "application/json"
    }
    current_url = f"https://api.clashofclans.com/v1/clans/{enc_tag}/currentwar"
    curr_resp   = requests.get(current_url, headers=headers)

    if curr_resp.status_code == 404:
        return await interaction.followup.send("This clan is not in a CWL war right now.")
    if curr_resp.status_code != 200:
        return await interaction.followup.send(
            f"Error fetching CWL state: {curr_resp.status_code}"
        )

    curr_data = curr_resp.json()
    state     = curr_data.get("state", "Unknown")

    # 4) choose source of .get('clans', [])
    if state == "preparation":
        clans = curr_data.get("clans", [])
    else:
        league_url  = (
            f"https://api.clashofclans.com/v1/"
            f"clans/{enc_tag}/currentwar/leaguegroup"
        )
        league_resp = requests.get(league_url, headers=headers)
        if league_resp.status_code != 200:
            return await interaction.followup.send(
                f"Error fetching league group: {league_resp.status_code}"
            )
        clans = league_resp.json().get("clans", [])

    # 5) find the requested clan
    match = None
    for clan in clans:
        name = clan["name"].lower()
        tag  = clan["tag"].lstrip("#").upper()

        if is_tag and tag == search_tag:
            match = clan
            break
        if not is_tag and name == search_name:
            match = clan
            break

    if not match:
        return await interaction.followup.send(
            f"Clan `{nameortag}` not found in CWL ({state})."
        )

    # 6) sort & format members
    sorted_m = sorted(
        match.get("members", []),
        key=lambda m: m["townHallLevel"],
        reverse=True
    )
    member_info = "\n".join(
        f"{i}. {m['name']} (TH {m['townHallLevel']})"
        for i, m in enumerate(sorted_m, start=1)
    )

    # 7) send result
    war_info = (
        "```yaml\n"
        "**CWL Clan Search Result**\n"
        f"State: {state}\n"
        f"Clan: {match['name']} (Tag: {match['tag']})\n"
        "Members:\n"
        f"{member_info}\n"
        "```"
    )
    await interaction.followup.send(war_info)


@bot.tree.command(name="playerinfo", description="Get player's general information")
@app_commands.describe(user="Select a Discord user", player_tag="The user's tag (optional)")
async def player_info(interaction: discord.Interaction, user: discord.Member = None, player_tag: str = None):
    cursor = get_db_connection()

    guild_id = interaction.guild.id

    # 1) FAST‐FAIL + fetch from DB (or provided_tag)
    try:
        tag = fetch_player_from_DB(cursor, guild_id, user, player_tag)
    except PlayerNotLinkedError as e:
        # "e" already contains the user.mention
        return await interaction.response.send_message(str(e), eFphemeral=True)
    except MissingPlayerTagError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)

    normalized_tag = tag.strip()
    try:
        player_data = get_player_data(normalized_tag)
    except Exception as e:
        return await interaction.response.send_message(
            f"Error getting player information: {e}",
            ephemeral=True
        )


    # 4) Build embed
    labels = player_data.get("labels", [])
    filtered_labels = ', '.join(label["name"] for label in labels) if labels else "None"
    player_name = player_data["name"]
    role = player_data["role"]
    preference = player_data["warPreference"]
    timestamp = int(time.time())

    role_mapping = {
        'admin': "Elder",
        'coLeader': "Co-Leader",
        'leader': "Leader",
        'member': "Member"
    }
    role = role_mapping.get(role, role)

    embed = discord.Embed(
        title=f"User: {player_name}, {player_data['tag']}",
        description=f"{filtered_labels}\nLast updated: <t:{timestamp}:R>",
        color=0x0000FF
    )
    embed.set_thumbnail(url=player_data['leagueTier']['iconUrls']['small'])
    embed.add_field(name="Clan Name", value=player_data['clan']['name'], inline=True)
    embed.add_field(name="Tag", value=player_data['clan']['tag'], inline=True)
    embed.add_field(name="Role", value=role, inline=True)
    embed.add_field(name="TH Lvl", value=player_data['townHallLevel'], inline=True)
    embed.add_field(name="Exp Lvl", value=player_data['expLevel'], inline=True)

    war_pref_icons = {'in': ":white_check_mark:", 'out': ":x:"}
    embed.add_field(name="War Preference", value=f"{war_pref_icons.get(preference, '')} {preference}", inline=True)

    embed.add_field(name="Trophies", value=f":trophy: {player_data['trophies']}", inline=True)
    embed.add_field(name="Best Trophies", value=f":trophy: {player_data['bestTrophies']}", inline=True)
    embed.add_field(name="War Stars", value=f":star: {player_data['warStars']}", inline=True)
    embed.add_field(name="Donated", value=f"{player_data['donations']:,}", inline=True)
    embed.add_field(name="Received", value=f"{player_data['donationsReceived']:,}", inline=True)
    embed.add_field(name="Capital Contributions", value=f"{player_data['clanCapitalContributions']:,}", inline=True)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="playertroops", description="Get a player's troop levels")
@app_commands.describe(user="Select a Discord user", player_tag="The user's tag (optional)", village="The type of village: home(default), builder or both")
async def player_troops(interaction: discord.Interaction, user: discord.Member = None, player_tag: str = None, village: str = "home"):
    cursor = get_db_connection()
    guild_id = interaction.guild.id

    try:
        tag = fetch_player_from_DB(cursor, guild_id, user, player_tag)
    except PlayerNotLinkedError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)
    except MissingPlayerTagError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)

    normalized_tag = tag.strip()
    try:
        player_data = get_player_data(normalized_tag)
    except Exception as e:
        return await interaction.response.send_message(
            f"Error getting player information: {e}",
            ephemeral=True
        )

    exclude_words = ['super', 'sneaky', 'ice golem', 'inferno', 'rocket balloon', 'ice hound']

    def is_valid_troop(troop):
        return all(word not in troop['name'].lower() for word in exclude_words)

    # Filter troops based on village type
    if village.lower() == 'builder':
        filtered_troops = [t for t in player_data['troops'] if t['village'] == 'builderBase' and is_valid_troop(t)]
    elif village.lower() == 'home':
        filtered_troops = [t for t in player_data['troops'] if t['village'] == 'home' and is_valid_troop(t)]
    else:
        filtered_troops = [t for t in player_data['troops'] if is_valid_troop(t)]

    # Split troops vs pets (LASSI and onwards are pets)
    troop_list = []
    pet_list = []
    pet_section = False

    for troop in filtered_troops:
        line = f"{troop['name']}: Level {troop['level']}/{troop['maxLevel']} {'(MAXED)' if troop['level'] == troop['maxLevel'] else ''}"
        if troop['name'].upper() == "L.A.S.S.I":  # first pet
            pet_section = True
        if pet_section:
            pet_list.append(line)
        else:
            troop_list.append(line)

    troops_text = "\n".join(troop_list)
    pets_text = "\n".join(pet_list)

    troop_information = (
        f"```yaml\n"
        f"Name: {player_data['name']}\n"
        f"Tag: {player_data['tag']}\n"
        f"Troop Levels:\n{troops_text}\n"
        f"Pet Levels:\n{pets_text}\n"
        f"```\n"
    )

    await interaction.response.send_message(troop_information)

@bot.tree.command(name = "playerequipments", description = "Get info on all of a player's equipments")
@app_commands.describe(user= "Select a Discord User",player_tag = "The user's tag(optional)")
async def player_equips(interaction: discord.Interaction, user: discord.Member = None, player_tag: str = None):
    cursor = get_db_connection()
    guild_id = interaction.guild.id
    try:
        tag = fetch_player_from_DB(cursor, guild_id, user, player_tag)
    except PlayerNotLinkedError as e:
        # "e" already contains the user.mention
        return await interaction.response.send_message(str(e), eFphemeral=True)
    except MissingPlayerTagError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)
    normalized_tag = tag.strip()
    try:
        player_data = get_player_data(normalized_tag)
    except Exception as e:
        return await interaction.response.send_message(
            f"Error getting player information: {e}",
            ephemeral=True
        )
    name = player_data.get('name')
    filtered_equipment = player_data['heroEquipment']

# Categorizing equipment based on max level
    common_equips = [equip for equip in filtered_equipment if equip['maxLevel'] == 18]
    rare_equips = [equip for equip in filtered_equipment if equip['maxLevel'] == 27]

# Sorting both categories by level (descending)
    sorted_common = sorted(common_equips, key=lambda equip: equip['level'], reverse=True)
    sorted_rare = sorted(rare_equips, key=lambda equip: equip['level'], reverse=True)

# Format details
    def format_equips(equips, category):
        return f"** {category} Equipment: **\n" + '\n'.join([
            f"{equip['name']}: Level {equip['level']}/{equip['maxLevel']} {'(MAXED)' if equip['level'] == equip['maxLevel'] else ''}"
            for equip in equips
        ]) if equips else f"**No {category} Equipment found.**"

    equip_information = (
        f"""```yaml
Name: {name}
Tag: {player_data['tag']}
{format_equips(sorted_common, "Common")}
{format_equips(sorted_rare, "Epic")}
```""")
    
    await interaction.response.send_message(equip_information)


@bot.tree.command(name = "playerspells", description = "Get player's spell levels")
@app_commands.describe(user = "Select a Discord User", player_tag = "The user's tag (optional)")
async def player_spells(interaction: discord.Interaction, user: discord.Member= None, player_tag: str = None):
    cursor = get_db_connection()
    guild_id = interaction.guild_id
    try:
        tag = fetch_player_from_DB(cursor, guild_id, user, player_tag)
    except PlayerNotLinkedError as e:
        # "e" already contains the user.mention
        return await interaction.response.send_message(str(e), eFphemeral=True)
    except MissingPlayerTagError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)

    normalized_tag = tag.strip()
    try:
        player_data = get_player_data(normalized_tag)
    except Exception as e:
        return await interaction.response.send_message(
            f"Error getting player information: {e}",
            ephemeral=True
        )
    
    name = player_data.get('name')
    

    #Iterates through the player_data spells and takes each index of spell and adds it to our list of spells
    #The first spell is the variable that will hold each individual item from the list as you iterate through it. It's the name you assign to each element in the list during the iteration.
    #The second spell is part of the expression for spell in player_data['spells'], where player_data['spells'] is the list you're iterating over.
    filtered_spells = [spell for spell in player_data['spells']] 
    #Makes a list and iterates through each spell  
    spell_details = '\n'.join([
        f"{spell['name']}: Level {spell['level']}/{spell['maxLevel']} {'(MAXED)' if spell['level'] == spell['maxLevel'] else ''}"
        for spell in filtered_spells
    ]) 

    spell_information = (
        f"```yaml\n"
        f"Name: {name} \n"
        f"Tag: {player_data['tag']}\n"
        f"{spell_details}\n"
        f"```\n"
    )
    await interaction.response.send_message(f'{spell_information}')






bot.run(TOKEN)

    