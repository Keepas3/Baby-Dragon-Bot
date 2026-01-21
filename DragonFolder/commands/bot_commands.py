import discord
from discord.ext import commands
from discord import app_commands, Embed
import random
import time
import coc

# Import helpers from config and utils
from config import get_db_cursor, coc_client
from utils import (
    fetch_clan_from_db, fetch_player_from_DB, get_clan_data, 
    check_coc_clan_tag, check_coc_player_tag, get_player_data,
    ClanNotSetError, PlayerNotLinkedError, MissingPlayerTagError
)

class BotCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="announce", description="Make an announcement")
    async def announce(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message(message)

    @app_commands.command(name="flipcoin", description="Flip coin (heads or tails)")
    async def flip(self, interaction: discord.Interaction):
        result = "Heads!!!" if random.randint(1, 2) == 1 else "Tails!!!"
        await interaction.response.send_message(f"The coin flips to... {result}")

    @app_commands.command(name="botstatus", description="Get the server status")
    async def server_status(self, interaction: discord.Interaction):
        cursor = get_db_cursor()
        guild_id = interaction.guild.id
        server_count = len(self.bot.guilds)
        user_count = len(self.bot.users)

        cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
        row = cursor.fetchone()
        clan_tag = row[0] if row else "No clan tag set"

        cursor.execute("SELECT discord_username, player_tag FROM players WHERE guild_id = %s", (guild_id,))
        players = cursor.fetchall()
        player_info = "\n".join([f"@{u} - {t or 'Not Linked'}" for u, t in players]) if players else "No linked players."

        embed = Embed(
            title=f"Status for {interaction.guild.name}",
            description=f"**Servers:** {server_count}\n**Users:** {user_count}\n\n**Clan:** {clan_tag}\n\n**Linked:**\n{player_info}",
            color=0x3498db
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='setclantag', description="Set the clan tag for this server")
    async def set_clan_tag(self, interaction: discord.Interaction, new_tag: str):
        clean_tag = new_tag.strip().upper()
        if not clean_tag.startswith("#"): clean_tag = f"#{clean_tag}"
        if await check_coc_clan_tag(clean_tag):
            cursor = get_db_cursor()
            cursor.execute("UPDATE servers SET clan_tag = %s WHERE guild_id = %s", (clean_tag, interaction.guild.id))
            await interaction.response.send_message(f"Clan tag updated to **{clean_tag}**!")
        else:
            await interaction.response.send_message("Invalid Clan Tag.", ephemeral=True)

    @app_commands.command(name='link', description="Link your CoC account")
    async def link(self, interaction: discord.Interaction, player_tag: str):
        clean_tag = player_tag.strip().upper()
        if not clean_tag.startswith("#"): clean_tag = f"#{clean_tag}"
        if await check_coc_player_tag(clean_tag):
            cursor = get_db_cursor()
            cursor.execute("""
                INSERT INTO players (discord_id, discord_username, guild_id, guild_name, player_tag)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE player_tag = VALUES(player_tag)
            """, (interaction.user.id, interaction.user.name, interaction.guild.id, interaction.guild.name, clean_tag))
            await interaction.response.send_message(f"Linked to **{clean_tag}**!")
        else:
            await interaction.response.send_message("Invalid player tag.", ephemeral=True)

    @app_commands.command(name='unlink', description="Unlink your CoC account")
    async def unlink(self, interaction: discord.Interaction):
        cursor = get_db_cursor()
        cursor.execute("DELETE FROM players WHERE discord_id = %s AND guild_id = %s", (interaction.user.id, interaction.guild.id))
        await interaction.response.send_message("Account unlinked.")

async def setup(bot):
    await bot.add_cog(BotCommands(bot))