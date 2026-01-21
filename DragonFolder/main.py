import discord
import os
import asyncio
from discord.ext import commands
# Import bot and other setups from your config file
from config import TOKEN, coc_client, initialize_coc, bot 

async def load_extensions():
    """Loops through the commands/ folder and loads every .py file."""
    # We look inside the folder you named 'commands'
    for filename in os.listdir('./commands'):
        if filename.endswith('.py'):
            # This converts 'bot_commands.py' to 'commands.bot_commands'
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

if __name__ == "__main__":
    try:
        asyncio.run(setup())
    except KeyboardInterrupt:
        pass