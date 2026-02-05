import os
import sys


sys.path.append(os.path.join(os.getcwd(), 'DragonFolder'))
import asyncio
import discord
from discord.ext import commands
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from config import TOKEN, coc_client, get_db_cursor, initialize_coc, bot 


async def load_extensions():
    """Loops through the commands/ folder and loads every .py file."""
    # We look inside the folder you named 'commands'
    commands_dir = os.path.join(current_dir, 'commands')
    
    if not os.path.exists(commands_dir):
        print(f"❌ Error: Could not find commands directory at {commands_dir}")
        return

    for filename in os.listdir(commands_dir):
        if filename.endswith('.py'):
            # Convert filename to extension syntax: 'commands.war_commands'
            extension_name = f'commands.{filename[:-3]}'
            try:
                await bot.load_extension(extension_name)
                print(f"Successfully loaded: {extension_name}")
            except Exception as e:
                print(f"Failed to load {extension_name}: {e}")

async def setup():
    """The main manager that runs before the bot starts."""
    async with bot:
        # 1. Start the Clash of Clans connection
        await initialize_coc() 
        
        # 2. Call the function to load your command files
        await load_extensions() 
        # Inside your setup_hook or main function
        #await bot.add_cog(WarPatrol(bot, coc_client))
        
        # 3. Final step: Launch the bot
        # NOTE: Syncing is moved to on_ready to avoid MissingApplicationID error
        await bot.start(TOKEN) 

@bot.event
async def on_ready():
    """Triggered when the bot is officially connected to Discord."""
    try:
        # Syncing here ensures the Application ID is retrieved first
        await bot.tree.sync() 
        print(f'Logged in as {bot.user} and commands synced!')
    except Exception as e:
        print(f"Error syncing tree: {e}")
        
    await bot.change_presence(activity=discord.Game(name='Playing with Fire'))

@bot.event
async def on_guild_join(guild):
    """Fires when the bot joins a new server. Initializes DB entry."""
    print(f"Joined new guild: {guild.name} ({guild.id})")
    try:
        cursor = get_db_cursor()
        # INSERT IGNORE prevents errors if the bot was previously in the server
        cursor.execute("""
            INSERT IGNORE INTO servers (guild_id, guild_name) 
            VALUES (%s, %s)
        """, (str(guild.id), guild.name))
        
        # Optional: Say hi
        if guild.system_channel:
            await guild.system_channel.send("Baby Dragon Bot has arrived! Use `/setclantag` to get started.")
    except Exception as e:
        print(f"DB Error on guild join: {e}")

@bot.event
async def on_guild_remove(guild):
    """Fires when the bot is kicked or leaves. Cleans up DB."""
    print(f"Removed from guild: {guild.name} ({guild.id})")
    try:
        cursor = get_db_cursor()
        # Clean up the server data and all linked player data for this guild
        cursor.execute("DELETE FROM servers WHERE guild_id = %s", (str(guild.id),))
        cursor.execute("DELETE FROM players WHERE guild_id = %s", (str(guild.id),))
        print(f"Successfully wiped data for {guild.name}")
    except Exception as e:
        print(f"DB Error on guild remove: {e}")
if __name__ == "__main__":
    try:
        asyncio.run(setup())
    except KeyboardInterrupt:
        pass