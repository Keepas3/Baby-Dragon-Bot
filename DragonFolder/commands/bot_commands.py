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
        await interaction.response.defer()
        
        try:
            cursor = get_db_cursor()
            guild_id = str(interaction.guild.id)
            
            cursor.execute("SELECT clan_tag, war_channel_id, raid_channel_id FROM servers WHERE guild_id = %s", (guild_id,))
            row = cursor.fetchone()
            
            # 1. Improved Safely check if row exists
            if row:
                clan_tag = f"`{row[0]}`" if row[0] else "❌ No clan tag set"
                war_mention = f"<#{row[1]}>" if row[1] else "❌ No war channel set"
                raid_mention = f"<#{row[2]}>" if row[2] else "❌ No raid channel set"
            else:
                clan_tag = "❌ Not Configured"
                war_mention = "❌ Run /setclantag"
                raid_mention = "❌ Run /setclantag"

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
            
            embed.add_field(name="Current Clan", value=f"`{clan_tag}`", inline=False)
            embed.add_field(name="⚔️ War Reminders", value=war_mention, inline=True)
            embed.add_field(name="🏰 Raid Reminders", value=raid_mention, inline=True)
            
            # Add a status check for the loops to make it feel "live"
            loop_status = "✅ Active" if self.war_reminder.is_running() else "⚠️ Stopped"
            embed.add_field(name="Bot Patrol Status", value=loop_status, inline=False)

            embed.add_field(name="Linked Members", value=player_info, inline=False)
            
            embed.set_footer(text=f"Serving {len(self.bot.guilds)} servers | {len(self.bot.users)} users")
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(f"Error in botstatus: {e}")
            await interaction.followup.send(f"❌ Error fetching status: `{e}`")

    @app_commands.command(name='setclantag', description="Set the clan tag and optional reminder channels")
    @app_commands.describe(
        new_tag="The #ClanTag", 
        war_channel="Optional: Channel for war reminders",
        raid_channel="Optional: Channel for capital raid reminders"
    )
    async def set_clan_tag(
        self, 
        interaction: discord.Interaction, 
        new_tag: str, 
        war_channel: discord.TextChannel = None,
        raid_channel: discord.TextChannel = None
    ):
        clean_tag = new_tag.strip().upper()
        if not clean_tag.startswith("#"): 
            clean_tag = f"#{clean_tag}"
        
        # 1. Validate the Tag with CoC API
        if not await check_coc_clan_tag(clean_tag):
            return await interaction.response.send_message("❌ Invalid Clan Tag. Please check the tag in-game.", ephemeral=True)

        cursor = get_db_cursor()
        guild_id = str(interaction.guild.id)
        
        # 2. Advanced Upsert Logic
        # We use COALESCE in the UPDATE section. 
        # This says: "If the new value is NULL, keep the old value that's already in the table."
        
        sql = """
            INSERT INTO servers (guild_id, guild_name, clan_tag, war_channel_id, raid_channel_id)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                clan_tag = VALUES(clan_tag),
                guild_name = VALUES(guild_name),
                war_channel_id = COALESCE(VALUES(war_channel_id), war_channel_id),
                raid_channel_id = COALESCE(VALUES(raid_channel_id), raid_channel_id)
        """
        
        # Convert objects to string IDs only if they were provided
        war_id = str(war_channel.id) if war_channel else None
        raid_id = str(raid_channel.id) if raid_channel else None
        
        cursor.execute(sql, (guild_id, interaction.guild.name, clean_tag, war_id, raid_id))

        # 3. Build a nice confirmation message
        msg = f"✅ **Clan Linked:** `{clean_tag}`\n"
        if war_channel:
            msg += f"⚔️ War Reminders: {war_channel.mention}\n"
        if raid_channel:
            msg += f"🏰 Raid Reminders: {raid_channel.mention}\n"
        
        if not war_channel and not raid_channel:
            msg += "*(Reminder channels were not changed)*"

        await interaction.response.send_message(msg)

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