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

def fetch_clan_from_db(cursor,guild_id: int,provided_tag: str = None) -> str:
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



def format_datetime(dt):
    """Handles coc.Timestamp objects or raw API strings."""
    if not dt or dt == "N/A":
        return "N/A"
    
    # Check if the input is a coc.Timestamp (which has a .time attribute)
    if hasattr(dt, 'time'):
        dt_obj = dt.time.replace(tzinfo=timezone.utc)
    else:
        # Fallback logic for raw strings if needed
        try:
            dt_obj = datetime.strptime(str(dt), '%Y%m%dT%H%M%S.%fZ').replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return "N/A"

    # Convert to EST (UTC-5)
    est = dt_obj.astimezone(timezone(timedelta(hours=-5)))
    return est.strftime('%Y-%m-%d %H:%M:%S %p EST')

def format_month_day_year(dt):
    """Prints just Month, Day, and Year for raid history."""
    if not dt or dt == "N/A":
        return "N/A"
    
    if hasattr(dt, 'time'):
        dt_obj = dt.time.replace(tzinfo=timezone.utc)
    else:
        try: 
            dt_obj = datetime.strptime(str(dt), '%Y%m%dT%H%M%S.%fZ').replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return "N/A"

    est = dt_obj.astimezone(timezone(timedelta(hours=-5)))
    return est.strftime('%m-%d-%Y')
    
def add_spaces(text):
    return re.sub(r'(?<!^)(?=[A-Z])', ' ', text)

    
# 1. Update Validation Functions
async def check_coc_clan_tag(clan_tag): 
    try:
        # get_clan automatically handles the tag normalization and API call
        await coc_client.get_clan(clan_tag)
        return True
    except coc.NotFound:
        return False
    except coc.ClashOfClansException:
        return False

async def check_coc_player_tag(player_tag): 
    try:
        await coc_client.get_player(player_tag)
        return True
    except coc.NotFound:
        return False
    except coc.ClashOfClansException:
        return False

# 2. Update Data Retrieval Function
async def get_clan_data(clan_tag: str):
    """
    Fetches clan data using the coc_client. 
    This automatically uses the whitelisted IP key managed by coc.py.
    """
    try:
        # You no longer need to manually encode tags like %23
        clan = await coc_client.get_clan(clan_tag)
        
        # coc.py returns an Object, but if you need a dict to keep the rest 
        # of your code working, you can use the .to_dict() helper.
        return clan
        
    except coc.NotFound:
        raise RuntimeError(f"Clash API Error (404): Clan {clan_tag} not found.")
    except coc.Maintenance:
        raise RuntimeError("Clash of Clans API is currently under maintenance.")
    except coc.ClashOfClansException as e:
        # This catches IP errors, invalid keys, etc.
        print(f"\n[!] CLASH API ERROR: {e}\n")
        raise RuntimeError(f"Clash API Error: {e}")

class ClanTagError(Exception):
    """Base exception for clan-tag lookup errors."""

class ClanNotSetError(ClanTagError):
    """Raised when no clan tag is set for this server."""
    def __init__(self):
        super().__init__("No clan tag is set for this server. Please set a clan tag using `/setclantag`.")

async def get_capital_raid_data(clan_tag: str):
    """
    Manually constructs a dictionary from RaidLogEntry objects.
    Maps coc.py attributes (like hall_level) to the keys used in your command.
    """
    try:
        # Fetch the raid log (returns a list of RaidLogEntry objects)
        raids = await coc_client.get_raid_log(clan_tag)
        
        items = []
        for raid in raids:
            # Construct the dictionary for each raid season
            raid_dict = {
                "state": raid.state,
                "startTime": raid.start_time, # Keep as object for format_datetime
                "endTime": raid.end_time,     # Keep as object for format_datetime
                "capitalTotalLoot": raid.total_loot,
                "totalAttacks": raid.attack_count,
                "offensiveReward": raid.offensive_reward,
                "defensiveReward": raid.defensive_reward,
                "enemyDistrictsDestroyed": raid.destroyed_district_count,
                
                # Mapping the attackLog using the RaidClan documentation provided
                "attackLog": [
                    {
                        "districts": [
                            {
                                "name": d.name,
                                "districtHallLevel": d.hall_level, # Mapping hall_level to districtHallLevel
                                "destructionPercent": d.destruction # Mapping destruction to destructionPercent
                            } for d in clan.districts
                        ]
                    } for clan in raid.attack_log # attack_log is a List[RaidClan]
                ],
                
                # Use Tag as the unique identifier for member tracking
                "members": [
                    {
                        "name": m.name,
                        "tag": m.tag,
                        "attacks": m.attack_count,
                        "capitalResourcesLooted": m.capital_resources_looted
                    } for m in raid.members
                ]
            }
            items.append(raid_dict)
        
        return {"items": items}
        
    except coc.NotFound:
        raise RuntimeError(f"Clash API Error (404): No raid data found for {clan_tag}.")
    except coc.ClashOfClansException as e:
        print(f"\n[!] CLASH API ERROR (Raid Data): {e}\n")
        raise RuntimeError(f"Clash API Error: {e}")
    
async def calculate_raid_season_stats(clan_tag: str):
    """Fetches raid data and prepares a clean dictionary for the command."""
    raid_data = await get_capital_raid_data(clan_tag)
    seasons = raid_data.get('items', [])
    
    if not seasons:
        return None

    entry = seasons[0] # This defines the 'entry' for the calculations
    
    # Member stats tracking by Tag to fix the "9 attacks" name bug
    member_stats = {} 
    for m in entry.get('members', []):
        m_tag = m.get('tag')
        if m_tag not in member_stats:
            member_stats[m_tag] = {"name": m.get('name'), "loot": 0, "atks": 0}
        member_stats[m_tag]["loot"] += m.get('capitalResourcesLooted', 0)
        member_stats[m_tag]["atks"] += m.get('attacks', 0)

    sorted_m = sorted(member_stats.values(), key=lambda x: x["loot"], reverse=True)
    stats_text = "\n".join([f"{i+1}. {m['name']}: {m['loot']:,} loot, {m['atks']} atks" for i, m in enumerate(sorted_m)])

    return {
        "state": entry.get('state', 'N/A'),
        "start": format_datetime(entry.get('startTime')),
        "end": format_datetime(entry.get('endTime')),
        "loot": entry.get('capitalTotalLoot', 0),
        "medals": calculate_medals(entry), # We call the math helper here!
        "stats_text": stats_text
    }
    
def calculate_medals(entry):
    """
    Calculates medals for a single raid entry. 
    Returns a string: 'Estimated Medals: X' (ongoing) or 'X' (ended).
    """
    state = entry.get('state', 'N/A')
    offensive_reward = entry.get('offensiveReward', 0)
    defensive_reward = entry.get('defensiveReward', 0)
    total_clan_attacks = entry.get('totalAttacks', 1) 

    if state == 'ongoing':
        raw_pool = 0
        attack_log = entry.get('attackLog', [])
        for clan in attack_log:
            for district in clan.get('districts', []):
                level = int(district.get('districtHallLevel', 0))
                if district.get('destructionPercent') == 100:
                    if district.get('name') == "Capital Peak":
                        medal_map = {10:1450, 9:1375, 8:1260, 7:1240, 6:1115, 5:810, 4:585, 3:360, 2:180}
                        raw_pool += medal_map.get(level, 0)
                    else:
                        medal_map = {5:460, 4:405, 3:350, 2:225, 1:135}
                        raw_pool += medal_map.get(level, 0)
        
        # Per-player estimate: (Total Pool / Clan Attacks) * 6
        estimate = (raw_pool / max(1, total_clan_attacks)) * 6
        return f"Estimated: {round(estimate):,}"
    
    else:
        # Final medals for completed raids
        final_total = (offensive_reward * 6.0) + defensive_reward
        return f"{round(final_total):,}"

async def get_current_war_data(clan_tag: str, war_tag: str = None):
    try:
        if war_tag:
            war = await coc_client.get_league_war(war_tag)
        else:
            war = await coc_client.get_current_war(clan_tag)
        
        if not war or war.state == 'notInWar':
            return None
            
        # Manually construct the dictionary for the command to use
        return {
            "state": war.state,
            "startTime": war.start_time, # Keep as object for format_datetime
            "endTime": war.end_time,
            "clan": {
                "tag": war.clan.tag,
                "name": war.clan.name,
                "stars": war.clan.stars,
                "destructionPercentage": war.clan.destruction,
                "attacks": war.clan.attacks_used,
                "total_attacks": war.clan.total_attacks,
                "max_stars": war.clan.max_stars,
                "badge": war.clan.badge.url,

                "members": [
                    {
                        "name": m.name,
                        "tag": m.tag,
                        "townhallLevel": m.town_hall,
                        "attacks": [
                            {
                                "stars": a.stars, 
                                "destructionPercentage": a.destruction
                            } for a in m.attacks
                        ]
                    } for m in war.clan.members
                ]
            },
            "opponent": {
                "tag": war.opponent.tag,
                "name": war.opponent.name,
                "stars": war.opponent.stars,
                "destructionPercentage": war.opponent.destruction,
                "badge": war.opponent.badge.url
            }
        }
    except coc.PrivateWarLog:
        raise RuntimeError("War data is private for this clan.")
    except coc.ClashOfClansException as e:
        raise RuntimeError(f"Clash API Error: {e}") 


async def get_cwl_data(clan_tag: str):
    try:
        group = await coc_client.get_league_group(clan_tag)
        if not group:
            return None
            
        return {
            "state": group.state,
            "season": group.season,
            "clans": [{"name": c.name, "tag": c.tag, "level": c.level} for c in group.clans],
            "rounds": [
                {"warTags": r.war_tags} for r in group.rounds
            ]
        }
    except coc.NotFound:
        return None 
    except coc.ClashOfClansException as e:
        raise RuntimeError(f"Clash API Error: {e}")

async def get_war_log_data(clan_tag: str):
    """
    Fetches the clan's war log.
    Returns raw coc.ClanWarLogEntry objects for use with Dot Notation.
    """
    try:
        # FIX: The correct method name is get_war_log (with underscore)
        war_log = await coc_client.get_war_log(clan_tag)
        
        # Return the list of raw objects directly
        return war_log
        
    except coc.PrivateWarLog:
        raise RuntimeError("The clan's war log is private.")
    except coc.NotFound:
        raise RuntimeError(f"No war log found for clan {clan_tag}.")
    except coc.ClashOfClansException as e:
        print(f"\n[!] CLASH API ERROR (War Log): {e}\n")
        raise RuntimeError(f"Clash API Error: {e}")




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

async def get_player_data(player_tag: str):
    """
    Fetches full player profile using coc_client.
    """
    try:
        # Returns a Player object with attributes like player.name, player.town_hall, etc.
        player = await coc_client.get_player(player_tag)
        return player
    except coc.NotFound:
        raise RuntimeError(f"Clash API Error (404): Player {player_tag} not found.")
    except coc.ClashOfClansException as e:
        raise RuntimeError(f"Clash API Error: {e}")


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
    cursor = get_db_connection()
    
    guild_id = interaction.guild.id

    # 1. Use 'await' because check_coc_clan_tag is an async function
    # 2. Pass the tag directly; coc.py handles the # encoding internally
    try:
        if await check_coc_clan_tag(new_tag):  
            # Update the database with the normalized tag
            cursor.execute(
                "UPDATE servers SET clan_tag = %s WHERE guild_id = %s", 
                (new_tag.upper(), guild_id)
            )
            db_connection.commit()
            
            await interaction.response.send_message(f'Clan tag has been updated to **{new_tag.upper()}** for this server!')
        else:
            await interaction.response.send_message("Not a valid Clan ID. Please check the tag and try again.")
    except Exception as e:
        await interaction.response.send_message(f"Error: The bot is still initializing or login failed. Details: {e}")
                  
          
@bot.tree.command(name='link', description="Link your Clash of Clans account to your Discord account")
async def link(interaction: discord.Interaction, player_tag: str):
    """Links a Clash of Clans account to the player's Discord ID and current server."""
    global db_connection, cursor
    cursor = get_db_connection()
    
    discord_id = interaction.user.id
    discord_username = interaction.user.name
    guild_id = interaction.guild.id
    guild_name = interaction.guild.name

    # 1. Normalize the tag (remove whitespace and make uppercase)
    clean_tag = player_tag.strip().upper()

    # 2. Use 'await' for the async validation function
    # No need for manual .replace('#', '%23') as coc.py handles this internally
    if await check_coc_player_tag(clean_tag):
        cursor.execute("""
            INSERT INTO players (discord_id, discord_username, guild_id, guild_name, player_tag)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                player_tag = VALUES(player_tag), 
                discord_username = VALUES(discord_username), 
                guild_name = VALUES(guild_name)
        """, (discord_id, discord_username, guild_id, guild_name, clean_tag))

        db_connection.commit()
        await interaction.response.send_message(
            f"Your Clash of Clans account with tag **{clean_tag}** has been linked to your Discord account!"
        )
    else:
        await interaction.response.send_message(
            f"**{clean_tag}** is not a valid player tag. Please check and try again."
        )

@bot.tree.command(name='unlink', description="Unlink your Clash of Clans account from your Discord account")
async def unlink(interaction: discord.Interaction):
    """Removes the player's linked Clash of Clans account from the database."""
    global db_connection, cursor
    cursor = get_db_connection()  
    
    discord_id = interaction.user.id
    guild_id = interaction.guild.id

    cursor.execute("SELECT player_tag FROM players WHERE discord_id = %s AND guild_id = %s", (discord_id, guild_id))
    result = cursor.fetchone()

    if not result:
        await interaction.response.send_message("You don't have a linked Clash of Clans account in this server.")
        return

    cursor.execute("DELETE FROM players WHERE discord_id = %s AND guild_id = %s", (discord_id, guild_id))
    db_connection.commit()

    await interaction.response.send_message("Your Clash of Clans account has been successfully unlinked.")


#Lists all clan members in clan 
@bot.tree.command(name="clanmembers", description="Get all member info of the clan sorted by League by default") 
@app_commands.describe(ranking="List by League(default), TH, role, tag")
async def clan_members(interaction: discord.Interaction, ranking: str = "LEAGUES"): 
    # 1. Database logic stays the same
    cursor = get_db_connection()
    guild_id = interaction.guild.id
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    result = cursor.fetchone()
    
    if not result or not result[0]:
        await interaction.response.send_message("No clan tag is set for this server.", ephemeral=True)
        return
    
    clan_tag = result[0]
    await interaction.response.defer()

    try:
        # 2. Fetch members using the async coc_client (No manual URL/Headers needed!)
        # This automatically handles Railway's dynamic IP
        members = await coc_client.get_members(clan_tag)
        
        member_list = f"```yaml\n** Members Ranked by {ranking}: ** \n"
        rank = ranking.lower()

        # 3. Sorting logic using Object Attributes
        # FIX 1: Use 'in' to check for multiple options correctly
        if rank in ["leagues", "league"]:
            # coc.py results are often sorted by rank/league by default
            sorted_members = members
        elif rank == "th":
            sorted_members = sorted(members, key=lambda m: m.town_hall, reverse=True)
        elif rank == "role":
            # FIX 2: Use exact coc.py internal names for the keys
            # 'admin' is the internal name for Elder
            role_order = {
                "leader": 1, 
                "co_leader": 2, 
                "elder": 3, 
                "member": 4
            }
            # Use m.role.name to match the internal strings above
            sorted_members = sorted(members, key=lambda m: role_order.get(m.role.name, 5))
        elif rank == "tag":
            sorted_members = sorted(members, key=lambda m: m.tag)
        else:
            await interaction.followup.send("Invalid ranking criteria.")
            return

        # 4. Generating member list using clean object properties
        for m in sorted_members:
            # Map role names to your preferred display format
            role_display = str(m.role)
            #print(role_display)
            #print(f"Member: {m.name} | Internal Role Name: {m.role.name}")
            
            if rank == "tag":
                member_info = f"{m.clan_rank}. {m.name}, {m.tag}\n"
            elif rank in ["leagues", "league"]:
                member_info = f"{m.clan_rank}. {m.name}, {role_display}, {m.league.name}\n"
            else: # TH or ROLE
                member_info = f"{m.clan_rank}. {m.name}, {role_display}, TH:{m.town_hall}\n"

            # Check message length (Discord 2000 char limit)
            if len(member_list) + len(member_info) > 1990:
                break
            member_list += member_info

        member_list += "```"
        await interaction.followup.send(member_list)

    except coc.ClashOfClansException as e:
        await interaction.followup.send(f"Error ftching members: {e}")


@bot.tree.command(name="lookupclans", description="search for clans")
@app_commands.describe(
    clanname="The clan's name", 
    war_frequency="Filter by war frequency (always)", 
    min_members="Filter by minimum num. of members", 
    max_members="Filter by maximum num. of members", 
    minclan_level="Filter by clan Level", 
    limits="Number of clans to return (default 1, max 3)"
)
async def lookup_clans(
    interaction: discord.Interaction, 
    clanname: str, 
    war_frequency: str = None, 
    min_members: int = None, 
    max_members: int = None, 
    minclan_level: int = None, 
    limits: int = 1
):
    # Ensure limits stay within requested bounds
    limits = max(1, min(limits, 3))

    await interaction.response.defer()

    try:
        # Fetch clans using coc_client. This handles parameters directly without manual URL building.
        # It also manages the authentication token for whatever IP Railway currently has.
        clans = await coc_client.search_clans(
            name=clanname,
            war_frequency=war_frequency,
            min_members=min_members,
            max_members=max_members,
            min_level=minclan_level,
            limit=limits
        )

        if not clans:
            await interaction.followup.send("No information found for the specified clan.")
            return

        for clan in clans:
            embed = Embed(
                title="Clan Information",
                color=0x3498db
            )
            
            # coc.py returns 'Clan' objects, so we use attribute notation (clan.name) 
            # instead of dictionary notation (clan['name']).
            embed.set_thumbnail(url=clan.badge.url)
            embed.add_field(name="Name", value=clan.name, inline=True)
            embed.add_field(name="Tag", value=clan.tag, inline=True)
            embed.add_field(name="Members", value=f":bust_in_silhouette: {clan.member_count} / 50", inline=False)
            embed.add_field(name="Clan Level", value=clan.level, inline=True)
            embed.add_field(name="Clan Points", value=clan.points, inline=True)
            embed.add_field(name="Min TownHall", value=str(clan.required_townhall), inline=False)
            embed.add_field(name="Req. Trophies", value=f":trophy: {clan.required_trophies}", inline=True)
            embed.add_field(name="Req. Builder Trophies", value=f":trophy: {clan.required_builder_base_trophies}", inline=True)

            if clan.public_war_log:
                embed.add_field(
                    name="Win/Loss Record", 
                    value=f"{clan.war_wins} :white_check_mark: / {clan.war_losses} :x:", 
                    inline=False
                )

            location_name = clan.location.name if clan.location else "N/A"
            embed.add_field(name="Location", value=f":globe_with_meridians: {location_name}", inline=False)

            await interaction.followup.send(embed=embed)

    except coc.ClashOfClansException as e:
        # Catches API errors, including maintenance or IP forbidden issues
        await interaction.followup.send(f"Error retrieving clan info: {e}")




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
        # 1. Await the async helper to get the coc.Clan object
        clan_data = await get_clan_data(normalized_clan_tag)
    except Exception as e:
        return await interaction.response.send_message(
            f"Error getting clan information: {e}",
            ephemeral=True
        )

    target = None
    timestamp = int(time.time())

    # 2. Use Object Attributes (Dot Notation) to find the member
    # coc.Clan objects use .members instead of ['memberList']
    if username:
        for member in clan_data.members:
            if member.name.lower() == username.lower():
                target = member
                break

    elif user:
        try:
            linked_tag = fetch_player_from_DB(cursor, guild_id, user, None)
            linked_tag = linked_tag.strip().upper()
            for member in clan_data.members:
                if member.tag.strip().upper() == linked_tag:
                    target = member
                    break
        except PlayerNotLinkedError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)
        except MissingPlayerTagError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)

    if target:
        # Mapping coc.Role object to display strings
        role_str = str(target.role).lower()
        role_display = "Elder" if role_str == 'admin' else "Co-Leader" if role_str == 'coleader' else role_str.capitalize()

        embed = discord.Embed(
            title=f"{target.name} — {target.tag}",
            color=discord.Color.green(),
            description=f"Last updated: <t:{timestamp}:R>"
        )
        
        # Access icons through nested objects
        if target.league:
            embed.set_thumbnail(url=target.league.icon.url)
            
        # Update field names to match coc.py object attributes
        embed.add_field(name="TownHall Level", value=str(target.town_hall), inline=True)
        embed.add_field(name="Clan Rank", value=str(target.clan_rank), inline=False)
        embed.add_field(name="Role", value=role_display, inline=True)
        
        league_name = target.league.name if target.league else "Unranked"
        embed.add_field(name="Trophies", value=f":trophy: {target.trophies} | {league_name}", inline=False)
        
        bb_league = target.builder_base_league.name if target.builder_base_league else "Unranked"
        embed.add_field(name="Builder Base Trophies", value=f":trophy: {target.builder_base_trophies} | {bb_league}", inline=False)
        
        # donationsReceived is shortened to .received in coc.py
        embed.add_field(name="Donations", value=f"Given: {target.donations} | Received: {target.received}", inline=False)

        return await interaction.response.send_message(embed=embed)

    return await interaction.response.send_message(
        f'User "{username or user.display_name}" not found in the clan.',
        ephemeral=True
    )



@bot.tree.command(name="claninfo", description="Retrieve information about the clan")
async def clanInfo(interaction: discord.Interaction):
    # 1. Fetch tag from DB
    cursor = get_db_connection()
    guild_id = interaction.guild.id
    try:
        tag = fetch_clan_from_db(cursor, guild_id)
    except ClanNotSetError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)

    normalized_tag = tag.strip().upper()

    # 2. Fetch clan data asynchronously
    try:
        # Await the async helper to get the coc.Clan object
        clan_data = await get_clan_data(normalized_tag)
    except Exception as e:
        return await interaction.response.send_message(
            f"Error getting clan information: {e}",
            ephemeral=True
        )

    # 3. Build embed using Object Attributes (Dot Notation)
    # coc.py uses snake_case for most attributes
    description = clan_data.description or "No description provided."
    timestamp   = int(time.time() // 60 * 60)  # Round to minute

    embed = Embed(
        title="Clan Information",
        description=f"Last updated: <t:{timestamp}:R>",
        color=0x3498db
    )
    
    # Access the badge URL through the badge object
    embed.set_thumbnail(url=clan_data.badge.url)
    embed.add_field(name="Name", value=clan_data.name, inline=True)
    embed.add_field(name="Tag", value=clan_data.tag, inline=True)

    # Use .member_count for the number of members
    embed.add_field(name="Members", value=f":bust_in_silhouette: {clan_data.member_count} / 50", inline=False)

    # Update field names to match coc.py object attributes
    embed.add_field(name="Level", value=clan_data.level, inline=True)
    
    # War frequency is accessed via .war_frequency
    freq_text = add_spaces(str(clan_data.war_frequency))
    embed.add_field(name="War Frequency", value=freq_text, inline=True)

    embed.add_field(name="Description", value=description, inline=False)
    embed.add_field(name="Min. TH Level", value=str(clan_data.required_townhall), inline=True)
    embed.add_field(name="Req. Trophies", value=f":trophy: {clan_data.required_trophies}", inline=True)
    embed.add_field(name="Req. Builder Base Trophies", value=f":trophy: {clan_data.required_builder_base_trophies}", inline=True)

    # .public_war_log is the correct attribute for visibility checks
    if clan_data.public_war_log:
        embed.add_field(
            name="War Win/Draw/Loss Record",
            value=f"{clan_data.war_wins} / {clan_data.war_ties} / {clan_data.war_losses}",
            inline=True
        )
        embed.add_field(name="War Streak", value=str(clan_data.war_win_streak), inline=True)

    # Access nested names via their respective objects
    if clan_data.war_league:
        embed.add_field(name="CWL League", value=clan_data.war_league.name, inline=False)
    
    if clan_data.capital_league:
        embed.add_field(name="Clan Capital League", value=clan_data.capital_league.name, inline=True)
        
    location_name = clan_data.location.name if clan_data.location else "Unknown"
    embed.add_field(name="Location", value=f":globe_with_meridians: {location_name}", inline=False)

    embed.set_footer(text=f"Requested by {interaction.user.name}")

    # 4. Send the final response
    await interaction.response.send_message(embed=embed)




@bot.tree.command(name="capitalraid", description="Retrieve information about current raid")
async def capitalraid(interaction: discord.Interaction):
    cursor = get_db_connection()
    guild_id = interaction.guild.id
    try:
        tag = fetch_clan_from_db(cursor, guild_id)
    except ClanNotSetError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)

    await interaction.response.defer()

    # This single line fetches the data, calculates medals, and formats members
    data = await calculate_raid_season_stats(tag)

    if not data:
        return await interaction.followup.send("No raid data found.")

    response = (
        f"```yaml\n"
        f"Status: {data['state']}\n"
        f"Start: {data['start']}\n"
        f"End: {data['end']}\n"
        f"Medals {data['medals']} | Total Loot: {data['loot']:,}\n"
        f"Member Stats:\n{data['stats_text']}\n"
        f"```"
    )
    await interaction.followup.send(response)


        
@bot.tree.command(name="previousraids", description="Retrieve information about capital raid seasons for the clan")
@app_commands.describe(limit="The number of raids to retrieve (default:2, max:5)")
async def previous_raids(interaction: discord.Interaction, limit: int = 2):
    cursor = get_db_connection()
    guild_id = interaction.guild.id

    # 1. Initial check (Fast-fail)
    try:
        tag = fetch_clan_from_db(cursor, guild_id)
    except ClanNotSetError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)

    normalized_tag = tag.strip().upper()

    # 2. Defer immediately to "buy time" for the async API call
    # This is critical for Railway deployments where network latency can vary.
    await interaction.response.defer()

    # 3. Fetch data using your async helper
    try:
        raid_data = await get_capital_raid_data(normalized_tag)
    except Exception as e:
        return await interaction.followup.send(f"Error getting clan information: {e}")

    seasons = raid_data.get('items', [])
    if not seasons:
        return await interaction.followup.send("No capital raid seasons found for the specified clan.")

    # 4. Limit the number of raids retrieved
    limit = max(2, min(limit, 5)) 

    for i, entry in enumerate(seasons[:limit]):
        state = entry.get('state', 'N/A')
        start_time = format_month_day_year(entry.get('startTime', 'N/A'))
        end_time = format_month_day_year(entry.get('endTime', 'N/A'))
        capital_total_loot = entry.get('capitalTotalLoot', 0)
        attacks = entry.get('totalAttacks', 0)
        districts_destroyed = entry.get('enemyDistrictsDestroyed', 0)
        
        # Use the helper to get either the estimate or the final count
        medal_display = calculate_medals(entry)

        colors = 0xffff00 if state == 'ongoing' else 0x1abc9c 

        embed = Embed(
            title=f"Raid #{i + 1}:",
            color=colors
        )
        embed.add_field(name="Status", value=state.capitalize(), inline=False)
        embed.add_field(name="Start Date", value=start_time, inline=True)
        embed.add_field(name="End Date", value=end_time, inline=True)
        embed.add_field(name="Capital Loot Obtained", value=f"{capital_total_loot:,}", inline=False)
        embed.add_field(name="Total Attacks", value=f"{attacks:,}", inline=True)
        embed.add_field(name="Districts Destroyed", value=districts_destroyed, inline=True)
        
        # Display the result from the helper
        embed.add_field(name="Raid Medals", value=medal_display, inline=False)
        
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
    
    try:
        # 1. Fetch raw objects (now a list of objects)
        war_entries = await get_war_log_data(tag)
        timestamp = int(time.time())

        if not war_entries:
            return await interaction.followup.send("No war log entries found.")

        limit = max(1, min(limit, 8))
        recent_wars = war_entries[:limit]

        # 2. Iterate using Dot Notation
        for entry in recent_wars:
            our_clan = entry.clan
            opp_clan = entry.opponent
            
            # Formatting values
            clan_destruction = round(our_clan.destruction, 2)
            opp_destruction = round(opp_clan.destruction, 2)
            opponent_name = opp_clan.name if opp_clan.name else "Unknown Opponent"
            
            # FIX: Cast Enum to string to allow comparison
            res = str(entry.result).lower() if entry.result else "unknown"
            
            if "win" in res:
                embed_color, result_text = 0x00ff00, "Result: :first_place: Win"
            elif "lose" in res:
                embed_color, result_text = 0xff0000, "Result: :second_place: Loss"
            else:
                embed_color, result_text = 0xffff00, f"Result: {res.capitalize()}"
            
            embed = Embed(
                title=f"{our_clan.name} vs {opponent_name}",
                description=f"{result_text}\n Last Updated: <t:{timestamp}:R>",
                color=embed_color
            )
            
            # Add fields based on regular war vs CWL (attacks_per_member)
            if entry.attacks_per_member == 2:
                embed.add_field(name="Clan Stars", value=f":star: {our_clan.stars}", inline=True)
                embed.add_field(name="Clan Destruction", value=f":fire: {clan_destruction}%", inline=True)
                embed.add_field(name="Opponent Stars", value=f":star: {opp_clan.stars}", inline=True)
                embed.add_field(name="Opponent Destruction", value=f":fire: {opp_destruction}%", inline=True)
            else:
                embed.add_field(name="CWL Stars", value=f":star: {our_clan.stars}", inline=True)
                embed.add_field(name="CWL Destruction", value=f":fire: {clan_destruction}%", inline=True)

            # FIX: Pass the raw Timestamp object to your formatter
            end_date = format_month_day_year(entry.end_time)
            embed.add_field(name="End Date", value=end_date, inline=False)
            
            await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"Error: {e}")



@bot.tree.command(name="currentwar", description="Get general info or member stats for current war (normal or CWL)")
async def currentwar(interaction: discord.Interaction, wartag: str = None, mode: str = "info"):
    cursor = get_db_connection()
    guild_id = interaction.guild.id
    
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    row = cursor.fetchone()

    if not row or not row[0]:
        return await interaction.response.send_message("No clan tag set for this server.", ephemeral=True)

    db_tag = row[0].strip().upper()
    await interaction.response.defer()

    try:
        war_data = await get_current_war_data(db_tag, wartag)
        
        if not war_data or war_data.get('state') == 'notInWar':
            return await interaction.followup.send("The clan is not currently in a war.")

        is_cwl = bool(wartag)
        source = "CWL" if is_cwl else "Normal"
        clanA, clanB = war_data.get("clan", {}), war_data.get("opponent", {})

        def clean(t): return t.strip().lstrip("#").upper()
        if is_cwl and clean(clanA.get("tag", "")) != clean(db_tag):
            our_block, opp_block = clanB, clanA
        else:
            our_block, opp_block = clanA, clanB

        # Correctly pull attacks and total from the specific clan block
        attacks = our_block.get("attacks", 0)
        total_attacks = our_block.get("total_attacks", 0)

        # MODE: General Info (Embed)
        if mode.lower() == "info":
            state = war_data.get("state", "Unknown")
            clan_stars, opp_stars = our_block.get("stars", 0), opp_block.get("stars", 0)
            
            # 1. Create the Embed first
            embed = Embed(
                title=f"{our_block.get('name','?')} vs {opp_block.get('name','?')}",
                description=f"{source} War — State: :crossed_swords: {state}\nLast Updated: <t:{int(time.time())}:R>",
                color=0x00ff00 if clan_stars > opp_stars else 0xff0000 if clan_stars < opp_stars else 0xffff00
            )
            
            # 2. Set the thumbnail using the badge from our_block
            if our_block.get("badge"):
                embed.set_thumbnail(url=our_block.get("badge"))
            
            embed.add_field(name="Start Time", value=format_datetime(war_data.get("startTime")), inline=True)
            embed.add_field(name="End Time", value=format_datetime(war_data.get("endTime")), inline=False)
            embed.add_field(name="Clan Stars", value=f":star: {clan_stars}", inline=True)
            embed.add_field(name="Opponent Stars", value=f":star: {opp_stars}", inline=False)
            embed.add_field(name="Clan Destruction", value=f"{round(our_block.get('destructionPercentage', 0), 2)}%", inline=True)
            embed.add_field(name="Opponent Destruction", value=f"{round(opp_block.get('destructionPercentage', 0), 2)}%", inline=True)
            embed.add_field(name="Total Attacks Used", value=f"{attacks} / {total_attacks}", inline=False)
            
            return await interaction.followup.send(embed=embed)

        # MODE: Player Stats (YAML)
        else:
            max_attacks = 1 if is_cwl else 2
            members = our_block.get("members", [])

            attacked, unattacked = [], []
            for m in members:
                atks = m.get("attacks", [])
                entry = {
                    "name": m.get("name"),
                    "th": m.get("townhallLevel"),
                    "stars": sum(a.get("stars", 0) for a in atks),
                    "pct": sum(a.get("destructionPercentage", 0) for a in atks),
                    "att": len(atks)
                }
                (attacked if entry["att"] > 0 else unattacked).append(entry)

            attacked.sort(key=lambda e: (e["stars"], e["pct"]), reverse=True)
            unattacked.sort(key=lambda e: (e["th"], e["name"]), reverse=True)

            lines = [f"```yaml\n{source} War Stats — {our_block.get('name')}", f"State: {war_data.get('state')}", f"Total Attacks Used: {attacks} / {total_attacks}", ""]
            lines.append("✅ Attacked")
            for i, e in enumerate(attacked, 1):
                lines.append(f"{i}. {e['name']}: Stars {e['stars']}, Destr {e['pct']}%, Atks {e['att']}/{max_attacks}")
            
            lines.append("\n❌ Not Attacked")
            for i, e in enumerate(unattacked, 1):
                lines.append(f"{i}. {e['name']}: TH {e['th']}, Atks 0/{max_attacks}")
            lines.append("```")

            await interaction.followup.send("\n".join(lines))

    except Exception as e:
        await interaction.followup.send(f"Error fetching war data: {e}")



        
@bot.tree.command(name="cwlschedule", description="Receive information about the current CWL Schedule")
async def cwlschedule(interaction: discord.Interaction):
    DEFAULT_CLAN_TAG = "#2JL28OGJJ"
    cursor = get_db_connection()
    guild_id = interaction.guild.id
    
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    row = cursor.fetchone()
    raw_tag = row[0] if row and row[0] else DEFAULT_CLAN_TAG

    await interaction.response.defer()

    try:
        # 1. Fetch the CWL league group using coc_client
        # This handles dynamic IP whitelisting automatically
        group = await coc_client.get_league_group(raw_tag)
        
        if not group:
            return await interaction.followup.send("This clan is not participating in CWL right now.")

        # 2. Build header & participating clans list using object attributes
        lines = [
            f"**CWL Season {group.season}** -  State: {group.state}",
            "",
            "Participating Clans:"
        ]
        for i, c in enumerate(group.clans, start=1):
            lines.append(f"{i}. {c.name} ({c.tag}) – Level {c.level}")

        lines.append("\nRound Schedule:")

        # 3. For each round, find your clan's war and the opponent name
        # We normalize tags for comparison
        my_norm = raw_tag.strip().lstrip("#").upper()

        for idx, round_data in enumerate(group.rounds, start=1):
            opponent_name = None
            found_war_tag = None

            # round_data.war_tags is a list of war tags in that round
            for wt in round_data.war_tags:
                if wt == "#0": continue
                
                # Fetch war details using the war tag
                war = await coc_client.get_league_war(wt)
                if not war: continue

                # Match your clan on either side of the war
                if war.clan.tag.strip().lstrip("#").upper() == my_norm:
                    opponent_name = war.opponent.name
                    found_war_tag = wt
                    break
                elif war.opponent.tag.strip().lstrip("#").upper() == my_norm:
                    opponent_name = war.clan.name
                    found_war_tag = wt
                    break

            if opponent_name:
                lines.append(f"Round {idx}: {opponent_name} (War Tag: {found_war_tag})")
            else:
                lines.append(f"Round {idx}: Not yet scheduled")

        text = "```yaml\n" + "\n".join(lines) + "\n```"
        await interaction.followup.send(text)

    except coc.ClashOfClansException as e:
        await interaction.followup.send(f"Error fetching CWL schedule: {e}")



@bot.tree.command(name="cwlclansearch", description="Search CWL clans by name or tag")
@app_commands.describe(nameortag="Clan name or tag")
async def cwlclansearch(interaction: discord.Interaction, nameortag: str):
    DEFAULT_CLAN_TAG = "#2JL28OGJJ"
    cursor = get_db_connection()
    guild_id = interaction.guild.id
    
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    row = cursor.fetchone()
    raw_tag = row[0] if row and row[0] else DEFAULT_CLAN_TAG

    query = nameortag.strip().upper()
    is_tag = query.startswith("#") or re.fullmatch(r"[0-9A-Z]+", query)

    await interaction.response.defer()

    try:
        # 1. Determine CWL state by checking current war first
        current_war = await coc_client.get_current_war(raw_tag)
        
        if not current_war or current_war.state == "notInWar":
            return await interaction.followup.send("This clan is not in a CWL war right now.")

        # 2. Get the list of clans based on state
        if current_war.state == "preparation":
            # In preparation, we use the clans associated with the current war
            # Note: For full CWL groups, league group is still preferred
            group = await coc_client.get_league_group(raw_tag)
            clans = group.clans if group else []
            state = "Preparation"
        else:
            group = await coc_client.get_league_group(raw_tag)
            clans = group.clans if group else []
            state = group.state if group else "Unknown"

        # 3. Find the matching clan
        match = None
        for clan in clans:
            if is_tag and clan.tag.strip().lstrip("#").upper() == query.lstrip("#"):
                match = clan
                break
            elif not is_tag and clan.name.upper() == query:
                match = clan
                break

        if not match:
            return await interaction.followup.send(f"Clan `{nameortag}` not found in CWL.")

        # 4. Fetch full clan details to get members (BasicClan doesn't always have full roster)
        # We use await coc_client.get_clan for the full member list
        full_clan = await coc_client.get_clan(match.tag)
        sorted_m = sorted(full_clan.members, key=lambda m: m.town_hall, reverse=True)

        member_info = "\n".join(
            f"{i}. {m.name} (TH {m.town_hall})" 
            for i, m in enumerate(sorted_m, start=1)
        )

        war_info = (
            "```yaml\n"
            "**CWL Clan Search Result**\n"
            f"State: {state}\n"
            f"Clan: {full_clan.name} ({full_clan.tag})\n"
            "Members:\n"
            f"{member_info}\n"
            "```"
        )
        await interaction.followup.send(war_info)

    except coc.ClashOfClansException as e:
        await interaction.followup.send(f"Error: {e}")


@bot.tree.command(name="playerinfo", description="Get player's general information")
@app_commands.describe(user="Select a Discord user", player_tag="The user's tag (optional)")
async def player_info(interaction: discord.Interaction, user: discord.Member = None, player_tag: str = None):
    cursor = get_db_connection()
    guild_id = interaction.guild.id

    # 1. Fetch the player tag from your database
    try:
        tag = fetch_player_from_DB(cursor, guild_id, user, player_tag)
    except PlayerNotLinkedError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)
    except MissingPlayerTagError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)

    normalized_tag = tag.strip()
    try:
        # 2. Await the async helper function to get the coc.Player object
        player_data = await get_player_data(normalized_tag)
    except Exception as e:
        return await interaction.response.send_message(
            f"Error getting player information: {e}",
            ephemeral=True
        )

    # 3. Update variables using Object Attributes (Dot Notation)
    # coc.py uses snake_case for attributes
    player_labels = ", ".join(label.name for label in player_data.labels) if player_data.labels else "None"
    timestamp = int(time.time())

    # Map the role object to your display string
    role_name = str(player_data.role).lower()
    role_mapping = {
        'admin': "Elder",
        'coleader': "Co-Leader",
        'leader': "Leader",
        'member': "Member"
    }
    display_role = role_mapping.get(role_name, role_name.capitalize())

    embed = discord.Embed(
        title=f"User: {player_data.name}, {player_data.tag}",
        description=f"{player_labels}\nLast updated: <t:{timestamp}:R>",
        color=0x0000FF
    )
    
    # coc.Player.league has an .icon.url attribute
    if player_data.league:
        embed.set_thumbnail(url=player_data.league.icon.url)
    
    # Accessing clan info through the player_data.clan object
    if player_data.clan:
        embed.add_field(name="Clan Name", value=player_data.clan.name, inline=True)
        embed.add_field(name="Tag", value=player_data.clan.tag, inline=True)
    
    embed.add_field(name="Role", value=display_role, inline=True)
    embed.add_field(name="TH Lvl", value=player_data.town_hall, inline=True)
    embed.add_field(name="Exp Lvl", value=player_data.exp_level, inline=True)

    # coc.py uses .war_opt_in which returns a boolean or specific string
    pref = player_data.war_opted_in or "Unknown"
    pref_icon = ":white_check_mark:" if pref.lower == "true" else ":x:"
    embed.add_field(name="War Preference", value=f"{pref_icon} {pref}", inline=True)

    embed.add_field(name="Trophies", value=f":trophy: {player_data.trophies}", inline=True)
    embed.add_field(name="Best Trophies", value=f":trophy: {player_data.best_trophies}", inline=True)
    embed.add_field(name="War Stars", value=f":star: {player_data.war_stars}", inline=True)
    embed.add_field(name="Donated", value=f"{player_data.donations:,}", inline=True)
    embed.add_field(name="Received", value=f"{player_data.received:,}", inline=True)
    embed.add_field(name="Capital Contributions", value=f"{player_data.clan_capital_contributions:,}", inline=True)

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
        # 1. Await the async helper to get the Player object
        player_data = await get_player_data(normalized_tag)
    except Exception as e:
        return await interaction.response.send_message(f"Error getting player information: {e}", ephemeral=True)

    # 2. Words to exclude (Super Troops, etc.)
    exclude_words = ['super', 'sneaky', 'ice golem', 'inferno', 'rocket balloon', 'ice hound']

    # 3. Use coc.py properties to filter by village automatically
    # coc.py provides .home_troops, .builder_troops, and .pets
    troop_list = []
    pet_list = []
    v_type = village.lower()

    # Define a helper to format the level string
    def format_lvl(item):
        max_str = '(MAXED)' if item.is_max else ''
        return f"{item.name}: Level {item.level}/{item.max_level} {max_str}"

    if v_type == 'builder':
        # Use .builder_troops attribute
        filtered = [t for t in player_data.builder_troops if all(w not in t.name.lower() for w in exclude_words)]
        troop_list = [format_lvl(t) for t in filtered]
    elif v_type == 'home':
        # Use .home_troops and .pets attributes
        filtered = [t for t in player_data.home_troops if all(w not in t.name.lower() for w in exclude_words)]
        troop_list = [format_lvl(t) for t in filtered]
        pet_list = [format_lvl(p) for p in player_data.pets]
    else: # 'both'
        filtered = [t for t in player_data.troops if all(w not in t.name.lower() for w in exclude_words)]
        troop_list = [format_lvl(t) for t in filtered]
        pet_list = [format_lvl(p) for p in player_data.pets]

    troops_text = "\n".join(troop_list) if troop_list else "None"
    pets_text = "\n".join(pet_list) if pet_list else "None"

    # 4. Use dot notation for name and tag
    troop_information = (
        f"```yaml\n"
        f"Name: {player_data.name}\n"
        f"Tag: {player_data.tag}\n"
        f"Troop Levels:\n{troops_text}\n"
        f"Pet Levels:\n{pets_text}\n"
        f"```\n"
    )

    await interaction.response.send_message(troop_information)

@bot.tree.command(name="playerequipments", description="Get info on all of a player's equipments")
@app_commands.describe(user="Select a Discord User", player_tag="The user's tag(optional)")
async def player_equips(interaction: discord.Interaction, user: discord.Member = None, player_tag: str = None):
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
        # 1. Await the async helper to get the Player object
        player_data = await get_player_data(normalized_tag)
    except Exception as e:
        return await interaction.response.send_message(
            f"Error getting player information: {e}",
            ephemeral=True
        )

    # 2. Use Object Attributes (Dot Notation)
    # coc.py uses .hero_equipment (list of equipment objects)
    filtered_equipment = player_data.equipment

    # Categorizing equipment based on max_level attribute
    # Common max level is 18, Epic max level is 27
    common_equips = [equip for equip in filtered_equipment if equip.max_level == 18]
    rare_equips = [equip for equip in filtered_equipment if equip.max_level == 27]

    # Sorting both categories by level (descending)
    sorted_common = sorted(common_equips, key=lambda equip: equip.level, reverse=True)
    sorted_rare = sorted(rare_equips, key=lambda equip: equip.level, reverse=True)

    # Format details using object properties like .name, .level, and .is_max
    def format_equips(equips, category):
        return f"** {category} Equipment: **\n" + '\n'.join([
            f"{equip.name}: Level {equip.level}/{equip.max_level} {'(MAXED)' if equip.is_max else ''}"
            for equip in equips
        ]) if equips else f"**No {category} Equipment found.**"

    equip_information = (
        f"```yaml\n"
        f"Name: {player_data.name}\n"
        f"Tag: {player_data.tag}\n"
        f"{format_equips(sorted_common, 'Common')}\n"
        f"{format_equips(sorted_rare, 'Epic')}\n"
        f"```"
    )
    
    await interaction.response.send_message(equip_information)

@bot.tree.command(name="playerspells", description="Get player's spell levels")
@app_commands.describe(user="Select a Discord User", player_tag="The user's tag (optional)")
async def player_spells(interaction: discord.Interaction, user: discord.Member = None, player_tag: str = None):
    cursor = get_db_connection()
    # 1. Fix: interaction.guild.id (not guild_id)
    guild_id = interaction.guild.id
    
    try:
        tag = fetch_player_from_DB(cursor, guild_id, user, player_tag)
    except PlayerNotLinkedError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)
    except MissingPlayerTagError as e:
        return await interaction.response.send_message(str(e), ephemeral=True)

    normalized_tag = tag.strip()
    try:
        # 2. Await the async helper to get the coc.Player object
        player_data = await get_player_data(normalized_tag)
    except Exception as e:
        return await interaction.response.send_message(
            f"Error getting player information: {e}",
            ephemeral=True
        )
    
    # 3. Use Object Attributes (Dot Notation)
    # coc.py uses .spells (a list of spell objects)
    filtered_spells = player_data.spells

    # Format details using object properties like .name, .level, .max_level, and .is_max
    spell_details = '\n'.join([
        f"{spell.name}: Level {spell.level}/{spell.max_level} {'(MAXED)' if spell.is_max else ''}"
        for spell in filtered_spells
    ]) 

    spell_information = (
        f"```yaml\n"
        f"Name: {player_data.name} \n"
        f"Tag: {player_data.tag}\n"
        f"{spell_details}\n"
        f"```\n"
    )
    await interaction.response.send_message(spell_information)






bot.run(TOKEN)

    