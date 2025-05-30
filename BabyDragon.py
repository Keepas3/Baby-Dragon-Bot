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
from datetime import datetime, timedelta, timezone
import random
import time
from PIL import Image, ImageDraw, ImageFont
import mysql.connector


# Connect to MySQL Database
conn = mysql.connector.connect(
    host=os.getenv("RAILWAY_TCP_PROXY_DOMAIN", "localhost"),  # Use Railway's public TCP Proxy
    user=os.getenv("MYSQLUSER", "root"),
    password=os.getenv("MYSQLPASSWORD", os.getenv("MY_SQL_PASSWORD")),
    database=os.getenv("MYSQLDATABASE", os.getenv("MY_SQL_DATABASE2")),
    port=os.getenv("RAILWAY_TCP_PROXY_PORT", "3306")  # Use Railway's external port
)

TOKEN = os.getenv('DISCORD_TOKEN2')
api_key = os.getenv('COC_api_key')
clan_tag = '#2QQ2VCU82'.replace('#', '%23')
og_clan_tag = '#2QQ2VCU82'


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix = "!", intents= intents)

def check_coc_player_tag(player_tag): 
    url = f'https://api.clashofclans.com/v1/players/{player_tag}' 
    headers = { 'Authorization': f'Bearer {api_key}', 'Accept': 'application/json' }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return True
    elif response.status_code == 404:
        return False

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


@bot.event
async def on_ready():
    """Fetch clan tags dynamically"""
    await bot.tree.sync()  # Sync commands globally
    await bot.change_presence(activity=discord.Game(name='With Fire'))

    for guild in bot.guilds:
        cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild.id,))
        result = cursor.fetchone()

        if result and result[0]:  # Ensure there's a valid clan tag
            clan_tag = result[0]
            # await guild.me.edit(nick=f"{bot.user.name} | {clan_tag}")  # Update bot's nickname
            # print(f"Updated bot nickname in {guild.name} to: {bot.user.name} | {clan_tag}")

    print(f'Logged in as {bot.user}!')



cursor = conn.cursor()

# cursor.execute("INSERT INTO servers (guild_id, guild_name) VALUES (%s, %s)", ("123456789", "Test Server"))
# conn.commit()

cursor.execute("SELECT * FROM servers")
result = cursor.fetchall()
print(result)  # Should return stored server data
def get_clan_tag(guild_id):
    """Retrieve the clan tag for a given Discord server."""
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    result = cursor.fetchone()
    
    if result and result[0]:  # Ensure there's a valid clan tag
        return result[0]
    else:
        return None  # Return None if no clan tag is set
@bot.event
async def on_guild_join(guild):
    """Automatically adds the guild_id to the database when bot joins a server."""
    cursor.execute("INSERT INTO servers (guild_id, guild_name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE guild_name = VALUES(guild_name)", (str(guild.id), guild.name))
    conn.commit()
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
            "`/currentwar` - Retrieve the clan's current war\n"
            "`/currentwarstats` - Display members' stats in current war\n"
            "`/cwlcurrent` - Retrieve the clan's current CWL and all rosters\n"
            "`/cwlspecificwars` - Retrieve individual war info in CWL\n"
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
            "`/playerheroes` - Get a player's heroes/equipments\n"
            "`/playerequipments` - Get info on all of a player's equipments\n"
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
    """Updates the clan tag in the database and changes the bot's nickname."""
    guild_id = interaction.guild.id  # Get current server ID

    if check_coc_clan_tag(new_tag.replace('#', '%23')):  # Validate the tag
        # Update the database
        cursor.execute("UPDATE servers SET clan_tag = %s WHERE guild_id = %s", (new_tag, guild_id))
        conn.commit()

        # Change the bot's nickname
        # await interaction.guild.me.edit(nick=f"{bot.user.name} | {new_tag}")
        
        await interaction.response.send_message(f'Clan tag has been updated to {new_tag} for this server!')
    else:
        await interaction.response.send_message(f"Not a valid Clan ID")
                  
          
@bot.tree.command(name='link', description="Link your Clash of Clans account to your Discord account")
async def link(interaction: discord.Interaction, player_tag: str):
    """Links a Clash of Clans account to the player's Discord ID and current server."""
    # player_tag = player_tag.replace('#', '%23')

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

        conn.commit()
        await interaction.response.send_message(f"Your Clash of Clans account with tag {player_tag} has been linked to your Discord account in this server.")

    else:
        await interaction.response.send_message(f"Not a valid player tag. Please check and try again.")

@bot.tree.command(name='unlink', description="Unlink your Clash of Clans account from your Discord account")
async def unlink(interaction: discord.Interaction):
    """Removes the player's linked Clash of Clans account from the database."""
    
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
    conn.commit()

    await interaction.response.send_message("Your Clash of Clans account has been successfully unlinked.")


#Lists all clan members in clan 
@bot.tree.command(name="clanmembers", description="Get all member info of the clan sorted by trophies by default") 
@app_commands.describe(ranking= "List by trophies(default), TH, role, tag")
async def clan_members(interaction: discord.Interaction, ranking: str = "TROPHIES"): 
    # Get the clan tag from the database for the current server
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
        if rank == "TROPHIES":
            sorted_members = sorted(clan_data['items'], key=lambda member: member['trophies'], reverse=True)
        elif rank == "TH":
            sorted_members = sorted(clan_data['items'], key=lambda member: member['townHallLevel'], reverse=True)
        elif rank == "ROLE":
            role_order = {"leader": 1, "coLeader": 2, "admin": 3, "member": 4}
            sorted_members = sorted(clan_data['items'], key=lambda member: role_order.get(member['role'], 5))
        elif rank == "TAG":
            sorted_members = sorted(clan_data['items'], key=lambda member: member['trophies'], reverse=True)
        else:
            await interaction.followup.send("Invalid ranking criteria. Please use: trophies, TH, role, or tag.")
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
            elif rank == "TROPHIES" or "TH" or "ROLE":
                member_info = (
                    f"{member['clanRank']}. {member['name']}, Role: {role}, (TH:{member['townHallLevel']})\n"
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
@app_commands.describe(user = "Select a Discord User", username = "A clan member's name(optional)")
async def user_info(interaction: discord.Interaction, user: discord.Member = None, username: str = None):
    if user:
        cursor.execute("SELECT player_tag FROM players WHERE discord_id = %s AND guild_id = %s", (user.id, interaction.guild.id))
        result = cursor.fetchone()
        if result and result[0]:
            player_tag = result[0]
        else:
            await interaction.response.send_message(f"{user.mention} has not linked a Clash of Clans account. Please provide their username manually.")
            return
        if not username:
            await interaction.response.send_message(f"Please provide a username for {user.mention} or mention a user who has linked their account.")
            return
    player_tag = player_tag.replace('#', '%23') if player_tag else None
    guild_id = interaction.guild.id
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    result = cursor.fetchone()

    if not result or not result[0]:
        await interaction.response.send_message("No clan tag is set for this server. Please set a clan tag using /setclantag.")
        return

    clan_tag = result[0].replace('#', '%23')  # Format the clan tag for the API request
    await interaction.response.defer()  # Defer the interaction to allow time for processing

    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        clan_data = response.json()
        user_found = False
        timestamp = int(time.time())

        for member in clan_data['memberList']:
            if member['name'].lower() == username.lower():
                role = member['role']
                embed = discord.Embed(
                    title=f"{member['name']}\n {member['tag']}",
                    color=discord.Color.green(),
                    description= f"Last updated: <t:{timestamp}:R>"
                )
             #   print(role)
                if role == 'admin':
                    role = "Elder"
                elif role == 'coLeader':
                    role = "Co-Leader"

                embed.set_thumbnail(url= member['league']['iconUrls']['small'])
                # embed.add_field(name="Player Tag", value=member['tag'], inline=True)
                embed.add_field(name="TownHall Level", value=str(member['townHallLevel']), inline=True)
                embed.add_field(name="Clan Rank", value=str(member['clanRank']), inline=False)
                embed.add_field(name="Role", value=role, inline=True)
                embed.add_field(name="Trophies", value=f":trophy: {member['trophies']} | {member['league']['name']}", inline=False)
                embed.add_field(name="Builder Base Trophies", value=f":trophy: {member['builderBaseTrophies']} | {member['builderBaseLeague']['name']}", inline=False)
                embed.add_field(name="Donations", value=f"Given: {member['donations']} | Received: {member['donationsReceived']}", inline=False)

                await interaction.followup.send(embed=embed)
                user_found = True
                break

        if not user_found:
            await interaction.followup.send(f'User "{username}" not found in the clan.')

    else:
        await interaction.followup.send(f"Error retrieving clan info: {response.status_code}, {response.text}")
                

@bot.tree.command(name="claninfo", description="Retrieve information about the clan")
async def clanInfo(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    result = cursor.fetchone()

    if not result or not result[0]:
        await interaction.response.send_message("No clan tag is set for this server. Please set a clan tag using /setclantag.")
        return
    
    clan_tag = result[0].replace('#', '%23')  # Format the clan tag for the API request
    await interaction.response.defer()
    if not api_key:
        raise ValueError("API KEY NOT FOUND")
    
    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        clan_data = response.json()
        description = clan_data['description']

        timestamp = int(time.time() //60 * 60) # Convert to seconds
        
        embed = Embed(
            title="Clan Information",
            description = f"Last updated: <t:{timestamp}:R>",
            color=0x3498db,
        )
        embed.set_thumbnail(url=clan_data['badgeUrls']['small'])
        embed.add_field(name="Name", value=f"{clan_data['name']}", inline=True)
        embed.add_field(name="Tag", value=clan_data['tag'], inline=True)

        embed.add_field(name="Members", value=f":bust_in_silhouette: {clan_data['members']} / 50", inline=False)

        embed.add_field(name="Clan Level", value=clan_data['clanLevel'], inline=True)
        embed.add_field(name="Clan Points", value=clan_data['clanPoints'], inline=True)

        embed.add_field(name="Description", value=description, inline=False)

        embed.add_field(name="Minimum TownHall Level", value=f"{clan_data['requiredTownhallLevel']}", inline=False)

        embed.add_field(name="Required Trophies", value=f":trophy: {clan_data['requiredTrophies']}", inline=True)
        embed.add_field(name="Required Builderbase Trophies", value=f":trophy: {clan_data['requiredBuilderBaseTrophies']}", inline=True)

        embed.add_field(name="Win/loss ratio", value=f"{clan_data['warWins']} :white_check_mark: / {clan_data['warLosses']} :x:", inline=False)
        embed.add_field(name="Location", value=f":globe_with_meridians: {clan_data['location']['name']}", inline=False)

        embed.set_footer(text=f"Requested by {interaction.user.name}")

        await interaction.followup.send(embed=embed)
    elif response.status_code == 404:
        await interaction.followup.send("No information found for the specified clan.")
    else:
        await interaction.followup.send(f"Error retrieving clan info: {response.status_code}, {response.text}")





@bot.tree.command(name="capitalraid", description="Retrieve information about info on current raid for clan")
async def capitalraid(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    result = cursor.fetchone()

    if not result or not result[0]:
        await interaction.response.send_message("No clan tag is set for this server. Please set a clan tag using /setclantag.")
        return
    clan_tag = result[0].replace('#', '%23')

    await interaction.response.defer()  # Defer the interaction to allow time for processing
    if not api_key:
        raise ValueError("API KEY NOT FOUND")
    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}/capitalraidseasons'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)
  #  print(f"Response status: {response.status_code}, Response text: {response.text}")  # Debugging print statement
    if response.status_code == 200:
        raid_data = response.json()
        # timestamp = int(time.time())

        seasons = raid_data.get('items', [])
        
        if not seasons:
            await interaction.followup.send("No capital raid seasons found for the specified clan.")
            return

        raid_info_list = []
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

                # reward = reward / total_attacks
                # print(reward)
                # reward = reward * 6.0
                # print(reward)
                # print(total_reward)
                raid_info = (
               # f"**Season #{i + 1}**\n"
                f"```yaml\n"
                f"Status: {state}\n"
                f"Start Time: {start_time}\n"
                f"End Time: {end_time}\n"
                f"Estimated Earning Medals: {round(reward)} | Total Loot: {capitalTotalLoot}\n"
                f"Member Loot Stats:\n{numbered_member_stats}\n"
                f"```\n"
            )
            elif state == 'ended' and defensive_reward !=0 and offensive_reward!=0:
                offensive_reward = offensive_reward * 6.0
                total_reward = offensive_reward + defensive_reward
                raid_info = (
               # f"**Season #{i + 1}**\n"
                f"```yaml\n"
                f"Status: {state}\n"
                f"Start Time: {start_time}\n"
                f"End Time: {end_time}\n"
                f"Raid Medals Earned: {round(total_reward)} | Total Loot Obtained: {capitalTotalLoot}\n"
                f"Member Loot Stats:\n{numbered_member_stats}\n"
                f"```\n"
            )
        
        raid_info_list.append(raid_info)
        
        chunk_size = 2000
        raid_info_message = "\n".join(raid_info_list)
        for i in range(0, len(raid_info_message), chunk_size):
            await interaction.followup.send(raid_info_message[i:i+chunk_size])
    elif response.status_code == 404:
        await interaction.followup.send("No capital raid seasons found for the specified clan.")
    else:
        await interaction.followup.send(f"Error retrieving capital raid seasons: {response.status_code}, {response.text}")


        
@bot.tree.command(name="previousraids", description="Retrieve information about capital raid seasons for the clan")
@app_commands.describe(limit="The number of raids to retrieve (default:2, max:5)")
async def previous_raids(interaction: discord.Interaction, limit: int = 2):
    guild_id = interaction.guild.id
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    result = cursor.fetchone()

    if not result or not result[0]:
        await interaction.response.send_message("No clan tag is set for this server. Please set a clan tag using /setclantag.")
        return
    clan_tag = result[0].replace('#', '%23')  # Format the clan tag for the API request
    await interaction.response.defer()  # Defer the interaction to allow time for processing
    if not api_key:
        raise ValueError("API KEY NOT FOUND")
    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}/capitalraidseasons'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)
    # print(f"Response status: {response.status_code}, Response text: {response.text}")  # Debugging print statement

    if response.status_code == 200:
        raid_data = response.json()
        seasons = raid_data.get('items', [])
        
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
            embed.add_field(name="Capital Loot Obtained", value=capital_total_loot, inline=False)
            embed.add_field(name="Total Attacks", value=attacks, inline=True)
            embed.add_field(name="Districts Destroyed", value=districts_destroyed, inline=True)
            if total_reward ==0:
                embed.add_field(name="Raid Medals Earned", value="Still Calculating...", inline=False)
            else:
                embed.add_field(name="Raid Medals Earned", value=round(total_reward), inline=False)
            
            # Send the embed for each raid
            await interaction.followup.send(embed=embed)

    elif response.status_code == 404:
        await interaction.followup.send("No capital raid seasons found for the specified clan.")
    else:
        await interaction.followup.send(f"Error retrieving capital raid seasons: {response.status_code}, {response.text}")


@bot.tree.command(name="warlog", description="Retrieve the war log for the specified clan")
@app_commands.describe(limit="The number of wars to retrieve (default 1, max 8)")
async def warLog(interaction: discord.Interaction, limit: int = 1):
    guild_id = interaction.guild.id
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,)) 
    result = cursor.fetchone()

    if not result or not result[0]:
        await interaction.response.send_message("No clan tag is set for this server. Please set a clan tag using /setclantag.")
        return
    clan_tag = result[0].replace('#', '%23')

    await interaction.response.defer()  # Defer the interaction to allow time for processing
    if not api_key:
        raise ValueError("API KEY NOT FOUND")

    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}/warlog'
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
    else:
        await interaction.followup.send(f"Error retrieving war log: {response.status_code}, {response.text}")



@bot.tree.command(name="currentwar", description="Receive general information about current war")
async def warInfo(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    result = cursor.fetchone()

    if not result or not result[0]:
        await interaction.response.send_message("No clan tag is set for this server. Please set a clan tag using /setclantag.")
        return
    
    clan_tag = result[0].replace('#', '%23')  # Format the clan tag for the API request
    await interaction.response.defer()  # Defer the interaction to allow time for processing


    if not api_key:
        raise ValueError("API KEY NOT FOUND")

    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}/currentwar'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        war_data = response.json()
        state = war_data['state']
        timestamp = int(time.time() // 60 * 60)  # Convert to seconds for the footer


        if state == 'inWar' or state == 'warEnded':
            start_time = format_datetime(war_data.get('startTime', 'N/A'))
            end_time = format_datetime(war_data.get('endTime', 'N/A'))
            num_of_attacks = war_data['teamSize'] * 2
            clan_stars = war_data['clan']['stars']
            opp_stars = war_data['opponent']['stars']
            destruction_percentage = round(war_data['clan']['destructionPercentage'], 2)
            opp_destruction_percentage = round(war_data['opponent']['destructionPercentage'], 2)


            # Create the embed
            embed = Embed(
                title=f"{war_data['clan']['name']} vs {war_data['opponent']['name']}",
                description=f"State: :crossed_swords: {state.capitalize()}\n Last Updated: <t:{timestamp}:R>",
                color=0x00ff00 if clan_stars > opp_stars #GREEN
                else 0xff0000 if clan_stars < opp_stars  #RED
                else 0x00ff00 if clan_stars == opp_stars and destruction_percentage > opp_destruction_percentage #GREEN
                else 0xff0000 if clan_stars == opp_stars and destruction_percentage < opp_destruction_percentage   #RED
                    else 0xffff00 # Green for winning ongoing wars, red is for losing ongoing wars, yellow for other
            )
            embed.add_field(name="Start Time", value=start_time, inline=True)
            embed.add_field(name="End Time", value=end_time, inline=True)

            embed.add_field(name="War Size", value=f":bust_in_silhouette: {war_data['teamSize']}", inline=False)

            if clan_stars > opp_stars:
                embed.add_field(name="Clan Tag", value=f":first_place: {war_data['clan']['tag']}", inline=True)
            else:
                embed.add_field(name="Clan Tag", value=f":second_place: {war_data['clan']['tag']}", inline=True)

            embed.add_field(name="Clan Stars", value=f":star: {clan_stars} (Attacks: {war_data['clan']['attacks']}/{num_of_attacks})", inline=True)
            embed.add_field(name="Clan Destruction", value=f":fire: {destruction_percentage}%", inline=True)

            if clan_stars < opp_stars:
                embed.add_field(name="Opponent Tag", value=f":first_place: {war_data['opponent']['tag']}", inline=True)
            else:
                embed.add_field(name="Opponent Tag", value=f":second_place: {war_data['opponent']['tag']}", inline=True)

            embed.add_field(name="Opponent Stars", value=f":star: {opp_stars} (Attacks: {war_data['opponent']['attacks']}/{num_of_attacks})", inline=True)
            embed.add_field(name="Opponent Destruction", value=f":fire: {opp_destruction_percentage}%", inline=True)

            embed.set_footer(text="Clash of Clans Current War Information")

            await interaction.followup.send(embed=embed)

        elif state == 'preparation':
            start_time = format_datetime(war_data.get('startTime', 'N/A'))
            end_time = format_datetime(war_data.get('endTime', 'N/A'))
            preparation_time = format_datetime(war_data.get('preparationStartTime', 'N/A'))

            # Create the embed
            embed = Embed(
                title="War Preparation",
                description="Current War is in preparation state.",
                color=0xFFFF00  # Yellow for preparation
            )
            embed.add_field(name="Preparation Start Time", value=preparation_time, inline=False)
            embed.add_field(name="Start Time", value=start_time, inline=True)
            embed.add_field(name="End Time", value=end_time, inline=True)
            embed.add_field(name="War Size", value=war_data['teamSize'], inline=False)
            embed.add_field(name="Clan", value=f"{war_data['clan']['name']} (Tag: {war_data['clan']['tag']})", inline=False)
            embed.add_field(name="Opponent", value=f"{war_data['opponent']['name']} (Tag: {war_data['opponent']['tag']})", inline=False)
            embed.set_footer(text="Clash of Clans War Preparation Info")

            await interaction.followup.send(embed=embed)

        elif state == 'notInWar':
            # Create the embed for not in war state
            embed = Embed(
                title="No Active War",
                description="The clan is currently not in war.",
                color=0xFF2C2C  # Blue for no war
            )
            embed.add_field(name="State", value=war_data['state'], inline=False)
            embed.set_footer(text="Clash of Clans Current War Info")

            await interaction.followup.send(embed=embed)

    elif response.status_code == 404:
        await interaction.followup.send("No current war found for the specified clan.")
    else:
        await interaction.followup.send(f"Error retrieving current war info: {response.status_code}, {response.text}")


@bot.tree.command(name = "currentwarstats", description = "Recieve player's information about current war")
async def warInfo(interaction:discord.Interaction):
    guild_id = interaction.guild.id
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    result = cursor.fetchone()

    if not result or not result[0]:
        await interaction.response.send_message("No clan tag is set for this server. Please set a clan tag using /setclantag.")
        return
    
    clan_tag = result[0].replace('#', '%23')  # Format the clan tag for the API request
    await interaction.response.defer() # Defer the interaction to allow time for processing 
    
    if not api_key:
        raise ValueError("API KEY NOT FOUND")
    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}/currentwar' 
    headers = { 'Authorization': f'Bearer {api_key}', 
    'Accept': 'application/json' 
    } 
    response = requests.get(url, headers=headers) 
   # print(f"Response status: {response.status_code}, Response text: {response.text}") # Debugging print statement
    if response.status_code == 200: 
        war_data = response.json() 
        war_state = war_data['state']
        print(war_state)
        members_with_attacks = []
        members_without_attacks = []
       

        if not war_data or 'state' not in war_data or not war_data['state']:
            # Handle the case where war_data['state'] is missing or empty
            await interaction.followup.send("No war specified or invalid war data received.")
            return
        elif war_state == 'preparation':
            await interaction.followup.send("War is preparing to start. There is no relevant stats listed yet.")
            return
        
        elif war_state == 'notInWar':
            war_info = (
                f"```yaml\n"
                f"**Current War Information**\n"
                f"State: {war_data['state']}\n"
                f"```\n"
        )
            await interaction.followup.send(war_info)
            return

        if war_state == 'inWar' or war_state == 'warEnded':
            start_time = format_datetime(war_data.get('startTime', 'N/A'))
            end_time = format_datetime(war_data.get('endTime', 'N/A'))
            numofAttacks = war_data['teamSize'] * 2
            clan = war_data.get('clan', [])
            members = clan.get('members', [])
         #   members = war_data['clan']['members']
          #  print(f"Members data: " + str(members))  # Debugging statement to see if the list is populated

            for member in members:
                member_name = member.get('name')
                th_lvl = member.get('townhallLevel')
                position = member.get('mapPosition')
                attacks = member.get('attacks',[])
               # print(f"Member Name: {member_name} {position} {attacks}")
                total_stars =0
                total_destruction =0
                total_attacks = len(attacks) # Counter for the number of attacks

                for attack in attacks:
                    obtained_stars = attack.get('stars', 0) 
                    destruction = attack.get('destructionPercentage', 0)
                    total_stars += obtained_stars
                    total_destruction += destruction
                    
                    
                member_data = ({
                    'name': member_name,
                    'townhallLevel': th_lvl,
                    'stars': total_stars,
                    'destruction': total_destruction,
                    'attacks': total_attacks
                })

                if total_attacks > 0:
                    members_with_attacks.append(member_data)
                else: 
                    members_without_attacks.append(member_data)

            # Sort by stars (descending) and destruction percentage (descending as a tiebreaker)
        sorted_with_attacks = sorted(members_with_attacks, key=lambda x: (x['stars'], x['destruction']), reverse=True)
        sorted_without_attacks = sorted(members_without_attacks, key=lambda x: (x['townhallLevel'], x['name']), reverse=True)

        if war_state == 'inWar':
            attackers_info = "```yaml\n**✅Members Who Already Attacked in Current War**\n"
        elif war_state == 'warEnded':
            attackers_info = "```yaml\n**✅Members Who Attacked in Most Recent War**\n"

        for i,member in enumerate(sorted_with_attacks):
            attackers_info += (f"{i+1}. {member['name']}: Stars: {member['stars']}, "
                 f"Percentage: {member['destruction']}%, "
                 f"Attacks: {member['attacks']}/2 \n")
        
        attackers_info += "```"

        if war_state == 'inWar':
            soon_to_be_attackers = "```yaml\n**❌Members Who Haven't Attacked in Current War**\n"
        if war_state == 'warEnded':
            soon_to_be_attackers = "```yaml\n**❌Members Who Didn't Attack in Most Recent War**\n"

        for i, member in enumerate(sorted_without_attacks):
            soon_to_be_attackers += (f"{i + 1}. {member['name']}: THlvl: {member['townhallLevel']}, "
            f"Attacks: {member['attacks']}/2\n")
                 
        soon_to_be_attackers +="```"
        await interaction.followup.send(attackers_info)
        await interaction.followup.send(soon_to_be_attackers)


    elif response.status_code == 404: 
        await interaction.followup.send("No current war found for the specified clan.")
    else:
        await interaction.followup.send(f"Error retrieving current war info: {response.status_code}, {response.text}")



@bot.tree.command(name="cwlcurrent", description="Receive information about the current CWL and its rosters")
async def warInfo(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    result = cursor.fetchone()

    if not result or not result[0]:
        await interaction.response.send_message("No clan tag is set for this server. Please set a clan tag using /setclantag.")
        return
    
    clan_tag = result[0].replace('#', '%23')  # Format the clan tag for the API request
    await interaction.response.defer()  # Defer interaction to allow time for processing

    if not api_key:
        raise ValueError("API KEY NOT FOUND")

    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}/currentwar/leaguegroup'
    headers = {'Authorization': f'Bearer {api_key}', 'Accept': 'application/json'}
    response = requests.get(url, headers=headers)

    if response.status_code == 200: 
        war_data = response.json()
        rounds = war_data.get('rounds', [])
 

        clan_info_list = []  # Stores clans with correct war tags

        for i, clan in enumerate(war_data.get('clans', [])):  # Ensure all 8 clans are processed
            correct_war_tag = None  # Initialize war tag as None

    # Make sure there are rounds and war tags available
            if i < len(rounds):
                war_tags = rounds[i].get('warTags', [])  # Get war tags for the corresponding round
                war_tags = [tag.replace('#', '%23') for tag in war_tags]  # Sanitize war tags

                for war_tag in war_tags:  # Loop through war tags
                    war_url = f'https://api.clashofclans.com/v1/clanwarleagues/wars/{war_tag}'
                    war_response = requests.get(war_url, headers=headers)

                    if war_response.status_code == 200:
                        war_details = war_response.json()


                        war_clan_tag = war_details.get('clan', {}).get('tag', 'Unknown')
                        opponent_tag = war_details.get('opponent', {}).get('tag', 'Unknown')
                    # war_state = war_details.get('state', 'N/A')

            
                        if war_clan_tag == og_clan_tag or opponent_tag == og_clan_tag:
                           # war_tag = war_tag.replace('%23', '#')
                            correct_war_tag = war_tag  # Assign the matching war tag
                            break  # Stop searching after finding a valid war tag

    # Add clan info with corresponding war tag,
            clan_info_list.append(
                f"Clan {i+1}: {clan['name']} (Tag: {clan['tag']}) - War Tag: {correct_war_tag or 'No valid war tag'}"
        )

        # Format response with both clan details and war info
        war_info = (
            f'```yaml\n'
            f"**Current CWL War Information**\n"
            f"State: {war_data.get('state', 'Unknown')}\n"
            f"Season: {war_data.get('season', 'Unknown')}\n"
            f"{chr(10).join(clan_info_list)}\n"
            f"```\n"
        )
        await interaction.followup.send(war_info)

    elif response.status_code == 404:
        await interaction.followup.send("Currently not in CWL.")
    else:
        await interaction.followup.send(f"Error retrieving current war info: {response.status_code}, {response.text}")


@bot.tree.command(name="cwlspecificwars", description="Receive general information about current war")
@app_commands.describe(war_tag = "The specific war tag for individual CWL War")
async def warInfo(interaction: discord.Interaction, war_tag: str):
    guild_id = interaction.guild.id
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    result = cursor.fetchone()

    if not result or not result[0]:
        await interaction.response.send_message("No clan tag is set for this server. Please set a clan tag using /setclantag.")
        return
    
    clan_tag = result[0].replace('#', '%23')  # Format the clan tag for the API request
    await interaction.response.defer()  # Defer the interaction to allow time for processing

    if not api_key:
        raise ValueError("API KEY NOT FOUND")

    url= f'https://api.clashofclans.com/v1/clanwarleagues/wars/{war_tag}'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        war_data = response.json()
        state = war_data['state']
        timestamp = int(time.time() // 60 * 60)  # Convert to seconds for the footer

        if state == 'inWar' or state == 'warEnded':
            start_time = format_datetime(war_data.get('startTime', 'N/A'))
            end_time = format_datetime(war_data.get('endTime', 'N/A'))
            num_of_attacks = war_data['teamSize'] 
            clan_stars = war_data['clan']['stars']
            opp_stars = war_data['opponent']['stars']

            cwl_clan_tag = war_data['clan']['tag']
            cwl_opp_tag = war_data['opponent']['tag']

            destruction_percentage = round(war_data['clan']['destructionPercentage'], 2)
            opp_destruction_percentage = round(war_data['opponent']['destructionPercentage'], 2)

            # Create the embed
            embed = Embed(
                title=f"{war_data['clan']['name']} vs {war_data['opponent']['name']}",
                description=f"State: {war_data['state'].capitalize()}\n Last Updated: <t:{timestamp}:R>",
                color=0x00ff00 if  cwl_clan_tag == og_clan_tag and clan_stars > opp_stars 
                else 0x00ff00 if  cwl_opp_tag == og_clan_tag and clan_stars < opp_stars 
                else 0xFFFF00 if  cwl_opp_tag == og_clan_tag and clan_stars == opp_stars 
                else 0x808080  # Green for winning  wars, red is for losing  wars, yellow for ties,  Gray for unknown results
            )
            if cwl_clan_tag == og_clan_tag: 
                embed.set_thumbnail(url=war_data['clan']['badgeUrls']['small'])
            elif cwl_opp_tag == og_clan_tag:
                embed.set_thumbnail(url= war_data['opponent']['badgeUrls']['small'])

            embed.add_field(name="Start Time", value=start_time, inline=True)
            embed.add_field(name="End Time", value=end_time, inline=True)

            embed.add_field(name="War Size", value=war_data['teamSize'], inline=False)

            embed.add_field(name="Clan Tag", value=war_data['clan']['tag'], inline=True)
            if {war_data['clan']['attacks']} == num_of_attacks:
                embed.add_field(name="Clan Stars", value=f":star: {clan_stars} (Attacks: {war_data['clan']['attacks']}/{num_of_attacks} :white_check_mark:)", inline=True)
            else:
                embed.add_field(name="Clan Stars", value=f":star: {clan_stars} (Attacks: {war_data['clan']['attacks']}/{num_of_attacks})", inline=True)

            if destruction_percentage == 100:
                embed.add_field(name="Clan Destruction", value=f":fire: {destruction_percentage}%", inline=True)
            else:
                embed.add_field(name="Clan Destruction", value=f":fire: {destruction_percentage}%", inline=True)

            embed.add_field(name="Opponent Tag", value=war_data['opponent']['tag'], inline=True)
            embed.add_field(name="Opponent Stars", value=f":star: {opp_stars} (Attacks: {war_data['opponent']['attacks']}/{num_of_attacks})", inline=True)
            embed.add_field(name="Opponent Destruction", value=f":fire: {opp_destruction_percentage}%", inline=True)

            embed.set_footer(text="Clash of Clans Current War Information")

            await interaction.followup.send(embed=embed)

        elif state == 'preparation':
            start_time = format_datetime(war_data.get('startTime', 'N/A'))
            end_time = format_datetime(war_data.get('endTime', 'N/A'))
            preparation_time = format_datetime(war_data.get('preparationStartTime', 'N/A'))

            # Create the embed
            embed = Embed(
                title="War Preparation",
                description=f"Current War is in preparation state.\n Last Updated: <t:{timestamp}:R>",
                color=0xFFFF00  # Yellow for preparation
            )
            embed.add_field(name="Preparation Start Time", value=preparation_time, inline=True)
            embed.add_field(name="Start Time", value=start_time, inline=True)
            embed.add_field(name="End Time", value=end_time, inline=True)
            embed.add_field(name="War Size", value=war_data['teamSize'], inline=True)
            embed.add_field(name="Clan", value=f"{war_data['clan']['name']} (Tag: {war_data['clan']['tag']})", inline=False)
            embed.add_field(name="Opponent", value=f"{war_data['opponent']['name']} (Tag: {war_data['opponent']['tag']})", inline=False)
            embed.set_footer(text="Clash of Clans War Preparation Info")

            await interaction.followup.send(embed=embed)

        elif state == 'notInWar':
            # Create the embed for not in war state
            embed = Embed(
                title="No Active War",
                description=f"The clan is currently not in war.\n Last Updated: <t:{timestamp}:R>",
                color=0xFF2C2C  # Blue for no war
            )
            embed.add_field(name="State", value=war_data['state'], inline=False)
            embed.set_footer(text="Clash of Clans Current War Info")

            await interaction.followup.send(embed=embed)

    elif response.status_code == 404:
        await interaction.followup.send("No current war found for the specified clan.")
    else:
        await interaction.followup.send(f"Error retrieving current war info: {response.status_code}, {response.text}")


@bot.tree.command(name = "cwlclansearch", description = "Search up other clans in CWL")
@app_commands.describe(clanname = "The clan's name")
async def CWL_clan_search(interaction: discord.Interaction, clanname: str):
    guild_id = interaction.guild.id
    cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
    result = cursor.fetchone()

    if not result or not result[0]:
        await interaction.response.send_message("No clan tag is set for this server. Please set a clan tag using /setclantag.")
        return
    
    clan_tag = result[0].replace('#', '%23')  # Format the clan tag for the API request
    await interaction.response.defer()
    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}/currentwar/leaguegroup'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        war_data = response.json()
        clan_found = False

        for clan in war_data.get('clans', []):
            if clan['name'].lower() == clanname.lower():
                clan_found = True
                sorted_members = sorted(clan['members'], key=lambda member: member['townHallLevel'], reverse=True)
                member_info = "\n".join([
                    f"Member{i+1}: {member['name']} (TH Level: {member['townHallLevel']})"
                   # for member in clan['members']
                    for i, member in enumerate(sorted_members)
                ])
                war_info = (
                    f'```yaml\n'
                    f"**CWL Clan Search Result**\n"
                    f"Clan: {clan['name']} (Tag: {clan['tag']})\n"
                    f"Members:\n{member_info}\n"
                    f"```\n"
                )
                await interaction.followup.send(war_info)
                break
        
        if not clan_found:
            await interaction.followup.send(f"Clan '{clanname}' not found in the current CWL.")
        elif response.status_code == 404: 
            await interaction.followup.send("Currently not in CWL.")    
    else:
        await interaction.followup.send(f"Error retrieving CWL information: {response.status_code}, {response.text}")

    


@bot.tree.command(name="playerinfo", description="Get player's general information")
async def player_info(interaction: discord.Interaction, user: discord.Member, player_tag: str = None):
    """Fetches player info by Discord user first, then falls back to player tag if needed."""

    # Check the database for the selected user's linked player tag
    cursor.execute("SELECT player_tag FROM players WHERE discord_id = %s AND guild_id = %s", (user.id, interaction.guild.id))
    result = cursor.fetchone()

    if result and result[0]:  # If a player tag is found, use it
        player_tag = result[0]
    elif not player_tag:  # If no player tag is found and none was provided, return an error
        await interaction.response.send_message(f"{user.mention} has not linked a Clash of Clans account. Please provide a player tag manually.")
        return

    # Format player tag for API request
    player_tag = player_tag.replace('#', '%23')

    # Ensure API key exists
    if not api_key:
        raise ValueError("API KEY NOT FOUND")

    # Fetch player data from Clash of Clans API
    url = f'https://api.clashofclans.com/v1/players/{player_tag}'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)

    
    if response.status_code == 200:
        player_data = response.json()
        labels = [label for label in player_data['labels']]
        filtered_labels = ', '.join([f"{label['name']}" for label in labels])
        player_name = player_data['name']
        role = player_data['role']
        preference = player_data['warPreference']

        timestamp = int(time.time())
    


        # Adjust role names
        role_mapping = {
            'admin': "Elder",
            'coLeader': "Co-Leader",
            'leader': "Leader",
            'member': "Member"
        }
        role = role_mapping.get(role, role)

        # Create Discord Embed
        embed = discord.Embed(
            title=f"User: {player_name}, {player_data['tag']}",
            description = f"{filtered_labels if filtered_labels else 'None'}\nLast updated: <t:{timestamp}:R>",
            color=0x0000FF  # Set an aesthetic color for the embed
        )
        embed.set_thumbnail(url=player_data['league']['iconUrls']['small'])
        embed.add_field(name="Clan Name", value=player_data['clan']['name'], inline=True)
        embed.add_field(name="Tag", value=player_data['clan']['tag'], inline=True)
        embed.add_field(name="Role", value=role, inline=True)
        embed.add_field(name="TH Lvl", value=player_data['townHallLevel'], inline=True)
        embed.add_field(name="Exp Lvl", value=player_data['expLevel'], inline=True)

        # War Preference
        war_pref_icons = {'in': ":white_check_mark:", 'out': ":x:"}
        embed.add_field(name="War Preference", value=f"{war_pref_icons.get(preference, '')} {preference}", inline=True)

        embed.add_field(name="Trophies", value=f":trophy:  {player_data['trophies']}", inline=True)
        embed.add_field(name="Best Trophies", value=f":trophy: {player_data['bestTrophies']}", inline=True)
        embed.add_field(name="War Stars", value=f":star: {player_data['warStars']}", inline=True)
        embed.add_field(name="Donated", value=player_data['donations'], inline=True)
        embed.add_field(name="Received", value=player_data['donationsReceived'], inline=True)
        embed.add_field(name="Capital Contributions", value=player_data['clanCapitalContributions'], inline=True)

        # Send the embed response
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"Error getting player information: {response.status_code}")

@bot.tree.command(name="playertroops", description="Get a player's troop levels")
@app_commands.describe(user="Select a Discord user", player_tag="The user's tag (optional)", village="The type of village: home(default), builder or both")
async def player_troops(interaction: discord.Interaction, user: discord.Member = None, player_tag: str = None, village: str = "home"):
    """Fetches troop levels by Discord user first, then falls back to player tag if needed."""

    # If a Discord user is provided, check the database for their player tag
    if user:
        cursor.execute("SELECT player_tag FROM players WHERE discord_id = %s AND guild_id = %s", (user.id, interaction.guild.id))
        result = cursor.fetchone()

        if result and result[0]:  # If a player tag is found, use it
            player_tag = result[0]
        else:
            await interaction.response.send_message(f"{user.mention} has not linked a Clash of Clans account. Please provide a player tag manually.")
            return

    # If no player tag is provided, return an error
    if not player_tag:
        await interaction.response.send_message("Please provide a player tag or mention a user who has linked their account.")
        return

    # Format player tag for API request
    player_tag = player_tag.replace('#', '%23')

    # Ensure API key exists
    if not api_key:
        raise ValueError("API KEY NOT FOUND")

    # Fetch player data from Clash of Clans API
    url = f'https://api.clashofclans.com/v1/players/{player_tag}'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        player_data = response.json()

        exclude_words = ['super', 'sneaky', 'ice golem', 'inferno', 'rocket balloon', 'ice hound']

        def is_valid_troop(troop):
            return all(word not in troop['name'].lower() for word in exclude_words)

        # Filter troops based on village type
        if village.lower() == 'builder':
            filtered_troops = [troop for troop in player_data['troops'] if troop['village'] == 'builderBase' and is_valid_troop(troop)]
        elif village.lower() == 'home':
            filtered_troops = [troop for troop in player_data['troops'] if troop['village'] == 'home' and is_valid_troop(troop)]
        else:
            filtered_troops = [troop for troop in player_data['troops'] if is_valid_troop(troop)]

        troops = '\n'.join([
            f"{troop['name']}: Level {troop['level']}/{troop['maxLevel']} {'(MAXED)' if troop['level'] == troop['maxLevel'] else ''}"
            for troop in filtered_troops])

        troop_information = (
            f"```yaml\n"
            f"Name: {player_data['name']}\n"
            f"Tag: {player_data['tag']}\n"
            f"**Troop Levels**\n"
            f"{troops}\n"
            f"```\n"
        )
        await interaction.response.send_message(f"{troop_information}")
    else:
        await interaction.response.send_message(f'Error: {response.status_code}, {response.text}')




@bot.tree.command(name="playerheroes", description="Get a player's heroes/equipments")
@app_commands.describe(user="Select a Discord user", player_tag="The user's tag (optional)", village="The type of village: home(default), builder or both")
async def player_heroes(interaction: discord.Interaction, user: discord.Member = None, player_tag: str = None, village: str = "home"):
    if user:
        cursor.execute("SELECT player_tag FROM players WHERE discord_id = %s AND guild_id = %s", (user.id, interaction.guild.id))
        result = cursor.fetchone()

        if result and result[0]:  # If a player tag is found, use it
            player_tag = result[0]
        else:
            await interaction.response.send_message(f"{user.mention} has not linked a Clash of Clans account. Please provide a player tag manually.", ephemeral=True)
            return
        
    if not player_tag:
        await interaction.response.send_message("Please provide a player tag or mention a user who has linked their account.", ephemeral=True)
        return

    playertag = player_tag.replace('#', '%23')
    url = f'https://api.clashofclans.com/v1/players/{playertag}'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        player_data = response.json()
        name = player_data.get('name')
        tag = player_data.get('tag')

        # Filter heroes (excluding builder base)
        if village.lower() == "home":
            filtered_heroes = [hero for hero in player_data.get('heroes', []) if hero['village'] == "home"]
        elif village.lower() == "builder":
            filtered_heroes = [hero for hero in player_data.get('heroes', []) if hero['village'] == "builderBase"]
        else:  # "both"
            filtered_heroes = player_data.get('heroes', [])
        hero_details = "\n".join([
            f"**{hero['name']}**: Level {hero['level']}/{hero['maxLevel']} {'(MAXED)' if hero['level'] == hero['maxLevel'] else ''}"
            for hero in filtered_heroes
        ])

        # Filter hero equipment
        filtered_equipment = [
            equipment for hero in player_data.get('heroes', []) if 'equipment' in hero for equipment in hero['equipment']
        ]
        equipment_details = "\n".join([
            f"**{equip['name']}**: Level {equip['level']}/{equip['maxLevel']} {'(MAXED)' if equip['level'] == equip['maxLevel'] else ''}"
            for equip in filtered_equipment
        ])
        if village.lower() == "home" or village.lower() == "both":
            hero_information = (
                f"```yaml\n"
                f"Name: {name} \n"
                f"Tag: {player_data['tag']}\n"
                f"** Hero Levels **\n"
                f"{hero_details}\n"
                f"** Equipment Levels **\n"
                f"{equipment_details}\n"
                f"```\n"
            )
        else:
            hero_information = (
                f"```yaml\n"
                f"Name: {name} \n"
                f"Tag: {player_data['tag']}\n"
                f"** Hero Levels **\n"
                f"{hero_details}\n"
                f"```\n"
            )
        await interaction.response.send_message(f'{hero_information}')
    else:
        await interaction.response.send_message(f'Error: {response.status_code}, {response.text}')

@bot.tree.command(name = "playerequipments", description = "Get info on all of a player's equipments")
@app_commands.describe(user= "Select a Discord User",player_tag = "The user's tag(optional)")
async def player_equips(interaction: discord.Interaction, user: discord.Member = None, player_tag: str = None):

    if user:
        cursor.execute("SELECT player_tag FROM players WHERE discord_id = %s AND guild_id = %s", (user.id, interaction.guild.id))
        result = cursor.fetchone()

        if result and result[0]:  # If a player tag is found, use it
            player_tag = result[0]

        else:
            await interaction.response.send_message(f"{user.mention} has not linked a Clash of Clans account. Please provide a player tag manually.")
            return
        
    if not player_tag:
        await interaction.response.send_message("Please provide a player tag or mention a user who has linked their account.")
        return
    # Format player tag for API request
    playertag = player_tag.replace('#', '%23')
    url = f'https://api.clashofclans.com/v1/players/{playertag}'
    headers = { 'Authorization': f'Bearer {api_key}',
    'Accept': 'application/json'
    }
    response = requests.get(url, headers = headers)
    if response.status_code == 200:
        player_data = response.json()
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
    else:
        await interaction.response.send_message(f'Error: {response.status_code}, {response.text}')


@bot.tree.command(name = "playerspells", description = "Get player's spell levels")
@app_commands.describe(user = "Select a Discord User", player_tag = "The user's tag (optional)")
async def player_spells(interaction: discord.Interaction, user: discord.Member= None, player_tag: str = None):

    if user:
        cursor.execute("SELECT player_tag FROM players WHERE discord_id = %s AND guild_id = %s", (user.id, interaction.guild.id))
        result = cursor.fetchone()

        if result and result[0]:  # If a player tag is found, use it
            player_tag = result[0]

        else:
            await interaction.response.send_message(f"{user.mention} has not linked a Clash of Clans account. Please provide a player tag manually.")
            return
        
    if not player_tag:
        await interaction.response.send_message("Please provide a player tag or mention a user who has linked their account.")
        return
    
    playertag = player_tag.replace('#', '%23')
    url= f'https://api.clashofclans.com/v1/players/{playertag}'
    headers ={ 'Authorization': f'Bearer {api_key}',
    'Accept': 'application/json'
    }
    response = requests.get(url, headers =headers)
    if response.status_code == 200:
        player_data = response.json()
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
    else:
        await interaction.response.send_message(f'Error: {response.status_code}, {response.text}')






bot.run(TOKEN)

    