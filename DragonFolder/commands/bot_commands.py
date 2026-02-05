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

    @app_commands.command(name="botstatus", description="Get the server configuration and status")
    async def server_status(self, interaction: discord.Interaction):
        cursor = get_db_cursor()
        guild_id = str(interaction.guild.id)
        
        # 1. Fetch Server Settings (Clan + Channel)
        cursor.execute("SELECT clan_tag, war_channel_id FROM servers WHERE guild_id = %s", (guild_id,))
        row = cursor.fetchone()
        
        clan_tag = row[0] if row and row[0] else "❌ No clan tag set"
        # Format the channel ID into a mention: <#123456789>
        channel_mention = f"<#{row[1]}>" if row and row[1] else "❌ No reminder channel set"

        # 2. Fetch Linked Players
        cursor.execute("SELECT discord_username, player_tag FROM players WHERE guild_id = %s", (guild_id,))
        players = cursor.fetchall()
        player_info = "\n".join([f"• @{u} ({t})" for u, t in players]) if players else "No linked players."

        # 3. Build the Polished Embed
        embed = discord.Embed(
            title=f"🛡️ {interaction.guild.name} Configuration",
            color=0x3498db,
            timestamp=interaction.created_at
        )
        
        embed.add_field(name="Current Clan", value=f"`{clan_tag}`", inline=True)
        embed.add_field(name="Reminder Channel", value=channel_mention, inline=True)
        
        
        embed.add_field(name="Linked Members", value=player_info, inline=False)
        
        embed.set_footer(text=f"Serving {len(self.bot.guilds)} servers | {len(self.bot.users)} users")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='setclantag', description="Set the clan tag and reminder channel")
    @app_commands.describe(new_tag="The #ClanTag", channel="Optional: Channel for war reminders")
    async def set_clan_tag(self, interaction: discord.Interaction, new_tag: str, channel: discord.TextChannel = None):
        clean_tag = new_tag.strip().upper()
        if not clean_tag.startswith("#"): clean_tag = f"#{clean_tag}"
        
        # 1. Use the selected channel, or the current one if none was picked
        target_channel_id = str(channel.id) if channel else str(interaction.channel.id)
        
        if await check_coc_clan_tag(clean_tag):
            cursor = get_db_cursor()
            # 2. Upsert (Update or Insert) the tag AND the channel ID
            cursor.execute("""
                INSERT INTO servers (guild_id, guild_name, clan_tag, war_channel_id)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    clan_tag = VALUES(clan_tag), 
                    war_channel_id = VALUES(war_channel_id),
                    guild_name = VALUES(guild_name)
            """, (str(interaction.guild.id), interaction.guild.name, clean_tag, target_channel_id))
            
            await interaction.response.send_message(
                f"✅ **Linked!**\nClan: **{clean_tag}**\nReminders will be sent to <#{target_channel_id}>"
            )
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
            """, (interaction.user.id, interaction.user.display_name, interaction.guild.id, interaction.guild.name, clean_tag))
            await interaction.response.send_message(f"Linked to **{clean_tag}**!")
        else:
            await interaction.response.send_message("Invalid player tag.", ephemeral=True)

    @app_commands.command(name='unlink', description="Unlink your CoC account")
    async def unlink(self, interaction: discord.Interaction):
        cursor = get_db_cursor()
        cursor.execute("DELETE FROM players WHERE discord_id = %s AND guild_id = %s", (interaction.user.id, interaction.guild.id))
        if cursor.rowcount > 0:
            await interaction.response.send_message("✅ Your Clash of Clans account has been unlinked from this server.")
        else:
            await interaction.response.send_message("❌ You don't have an account linked in this server.", ephemeral=True)

    
async def setup(bot):
    await bot.add_cog(BotCommands(bot))