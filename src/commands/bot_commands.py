from datetime import datetime
import discord
from discord.ext import commands
from discord import app_commands, Embed, ui, Interaction
import random
import time
import coc
import praw
import os
import json
import asyncio
from services.coc_worker import run_mission_worker

# INITIALIZE REDDIT AT THE TOP (Global Scope)
client_id = os.getenv('client_id')
client_secret = os.getenv('client_secret')
user_agent = os.getenv('user_agent')

reddit = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret, 
    user_agent=user_agent,
    check_for_async=False 
)

# Import helpers from config and utils
from config import get_db_connection, get_db_cursor, coc_client
from utils import (
    fetch_clan_from_db, fetch_player_from_DB, get_clan_data, 
    check_coc_clan_tag, check_coc_player_tag, get_player_data,
    ClanNotSetError, PlayerNotLinkedError, MissingPlayerTagError
)


class HelpView(ui.View):
    def __init__(self, summary_embed, full_embed):
        super().__init__(timeout=120)
        self.summary_embed = summary_embed
        self.full_embed = full_embed
        self.showing_all = False

    @ui.button(label="Show All Commands", style=discord.ButtonStyle.blurple)
    async def toggle_help(self, interaction: discord.Interaction, button: ui.Button):
        if not self.showing_all:
            button.label = "Show Less"
            button.style = discord.ButtonStyle.gray # Change color for "Show Less"
            self.showing_all = True
            await interaction.response.edit_message(embed=self.full_embed, view=self)
            
        else:
            button.label = "Show All Commands"
            button.style = discord.ButtonStyle.blurple
            self.showing_all = False
            await interaction.response.edit_message(embed=self.summary_embed, view=self)
# --- 🏰 UPDATED GLOBAL VERIFIED MODAL ---
class CoCLinkModal(discord.ui.Modal, title="Link Clash of Clans Account"):
    player_tag = discord.ui.TextInput(
        label="Player Tag",
        placeholder="#2PP92G2Y",
        required=True,
        max_length=15
    )
    
    api_token = discord.ui.TextInput(
        label="API Token / Verification Token",
        placeholder="Enter your 8-digit in-game API Token",
        required=True,
        min_length=8,
        max_length=8
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        clean_tag = self.player_tag.value.strip().upper()
        if not clean_tag.startswith("#"): 
            clean_tag = f"#{clean_tag}"
            
        token = self.api_token.value.strip()

        # Check tag validity
        if await check_coc_player_tag(clean_tag):
            try:
                # 1. Verify token with Supercell
                is_verified = await coc_client.verify_player_token(clean_tag, token)
                
                if not is_verified:
                    await interaction.followup.send(
                        "❌ **Verification Failed!** The API Token you entered does not match this player tag.\n\n"
                        "**How to find your token:**\n"
                        "1. Open Clash of Clans -> Settings -> More Settings.\n"
                        "2. Scroll to the bottom and click 'API Token'.\n"
                        "3. Re-run `/link` and enter your fresh token.",
                        ephemeral=True
                    )
                    return

                # 2. Save globally (No guild_id or guild_name needed!)
                conn = get_db_connection() 
                cursor = conn.cursor(buffered=True) 
                
                cursor.execute("""
                    INSERT INTO players (discord_id, discord_username, player_tag, is_premium)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        player_tag = VALUES(player_tag),
                        discord_username = VALUES(discord_username)
                """, (
                    str(interaction.user.id), 
                    interaction.user.display_name, 
                    clean_tag, 
                    0
                ))
                conn.commit() 
                cursor.close()
                conn.close()
                
                await interaction.followup.send(f"✅ **Account Verified!** You have successfully linked **{clean_tag}** globally to your Discord profile!")
                
            except Exception as e:
                print(f"💥 DB/API Error during Link: {e}")
                await interaction.followup.send("❌ A system error occurred while saving your profile.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Invalid player tag format.", ephemeral=True)


# --- 🛒 UPDATED GLOBAL LINK MENU VIEW ---
class LinkMenuView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=180)
        self.cog = cog

    # --- 🛒 UPDATED GLOBAL LINK MENU VIEW (With Step-by-Step Embeds) ---
class LinkMenuView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=180)
        self.cog = cog

    @discord.ui.button(label="Link CoC Account", style=discord.ButtonStyle.primary, emoji="🏰")
    async def link_coc(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Clean & Simple: Opens the modal globally.
        await interaction.response.send_modal(CoCLinkModal(self.cog))

    @discord.ui.button(label="Link Store (Cookies)", style=discord.ButtonStyle.success, emoji="🛒")
    async def link_store(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_dm = interaction.guild is None

        # 1. Create a beautiful, step-by-step registration instructions embed
        guide_embed = discord.Embed(
            title="🛒 Supercell Store Cookie Link Guide",
            description=(
                "Follow these simple steps on your computer to securely register your web store session. "
                "This allows the bot to automatically claim your weekly rewards!\n\n"
                "**⏳ I am waiting for your file (expires in 2 minutes)...**"
            ),
            color=discord.Color.green()
        )
        
        guide_embed.add_field(
            name="Step 1: Install a Cookie Exporter",
            value="Install a [Copy Cookies](https://chromewebstore.google.com/detail/copy-cookies/jcbpglbplpblnagieibnemmkiamekcdg) browser extension",
            inline=False
        )
        guide_embed.add_field(
            name="Step 2: Log Into Supercell Store",
            value="Go to the official [Clash of Clans Store](https://store.supercell.com/clashofclans) and sign in.",
            inline=False
        )
        guide_embed.add_field(
            name="3️Step 3: Export Your Cookies",
            value="Click on browser extension to copy the cookies",
            inline=False
        )
        guide_embed.add_field(
            name="Step 4: Upload it Here",
            value="Paste and send in Dragon Bot DM.",
            inline=False
        )

        if is_dm:
            # If already in DMs, send the guide directly
            await interaction.response.send_message(embed=guide_embed, ephemeral=True)
            asyncio.create_task(self.cog.handle_cookie_upload(interaction, interaction.user.id))
        else:
            try:
                # Attempt to DM the user the guide
                dm_channel = await interaction.user.create_dm()
                await dm_channel.send(embed=guide_embed)
                
                # Send an ephemeral confirmation embed inside the server channel
                status_embed = discord.Embed(
                    title="🔒 Security Check Sent!",
                    description=(
                        "To protect your web cookies, I have sent you a private direct message with step-by-step instructions.\n\n"
                        "**Please check your DMs to complete the registration!**"
                    ),
                    color=discord.Color.blue()
                )
                status_embed.set_footer(text="Ensure your server DM privacy settings are enabled!")
                
                await interaction.response.send_message(embed=status_embed, ephemeral=True)
                asyncio.create_task(self.cog.handle_cookie_upload(interaction, interaction.user.id, dm_channel))
                
            except discord.Forbidden:
                # If the user has DMs closed, show an instructional error embed
                fail_embed = discord.Embed(
                    title="❌ DM Delivery Failed",
                    description=(
                        "I was unable to send you a Direct Message.\n\n"
                        "**How to fix this:**\n"
                        "1. Go to your **Discord User Settings**.\n"
                        "2. Select **Privacy & Safety**.\n"
                        "3. Turn ON **'Allow direct messages from server members'**.\n"
                        "4. Click the **Link Store** button again!"
                    ),
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=fail_embed, ephemeral=True)

class BotCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Displays command guide")
    async def help_command(self, interaction: discord.Interaction):
        """Sends a toggleable command menu."""
        
        # VERSION A: Summary (Only the most important ones)
        summary_embed = discord.Embed(
            title="🐉 Dragon Bot | Quick Guide",
            description="Essential commands for daily usage. Click the button for the full list!",
            color=0x00FF00
        )
        summary_embed.add_field(name="🛡️ Clan Core", 
            value=(
                "> `/claninfo` — General clan overview\n"
                "> `/clanmembers` — Members ranked by leagues\n"
                "> `/currentwar` — Stats & Info for War/CWL\n"
                "> `/capitalraid` — Current Raid Weekend progress\n"
                "> `/cwlprep` — Scout matchup levels for current CWL\n"

        ), inline=True
        )

        summary_embed.add_field(name="⚔️ Player Core",
           value=(
                "> `/playerinfo` — General stats and clan-related info\n"
                "> `/playerheroes` — Check heroes, pets and equipment levels\n"
                "> `/searchmember` — Find a player in your current clan"
            ),
            inline=False)
        summary_embed.add_field(name="⚙️ Settings",
            value=(
                "> `/setclantag` — Link clan and set reminder channels\n"
                "> `/botstatus` — View current server config\n"
                "> `/link` / `/unlink` — Connect/disconnect CoC tag to Discord"
            ),
            inline=False
        )

        # VERSION B: Full (The master list)
            # 🛡️ Clan Management
        full_embed = discord.Embed(
            title="🐉 Dragon Bot | Master Command List",
            description="Complete list of all available tools and utilities.",
            color=0x00FF00
        )
        full_embed.add_field(
            name="🛡️ **Clan Management**",
            value=(
                "> `/claninfo` — General clan overview\n"
                "> `/clanmembers` — Members ranked by leagues\n"
                "> `/clansearch` — Search for a clan by name\n"
                "> `/capitalraid` — Current Raid Weekend progress\n"
                "> `/previousraids` — History of past Raid seasons\n"
                "> `/currentwar` — Stats & Info for War/CWL\n"
                "> `/warlog` — Check recent war history\n"
                "> `/cwlprep` — Scout matchup levels for current CWL\n"
                "> `/cwlschedule` — View CWL rounds and opponents\n"
                "> `/cwlclansearch` — Search opponent rosters and levels"
            ),
            inline=False
        )

        # ⚔️ Player Tools
        full_embed.add_field(
            name="⚔️ **Player Tools**",
            value=(
                "> `/playerinfo` — General stats and clan-related info\n"
                "> `/playerlevels` — Troops & Siege levels\n"
                "> `/playerheroes` — Check heroes, pets and equipment levels\n"
                "> `/searchmember` — Find a player in your current clan"
            ),
            inline=False
        )

        # ⚙️ Settings & Admin
        full_embed.add_field(
            name="⚙️ **Settings & Admin**",
            value=(
                "> `/setclantag` — Link clan and set reminder channels\n"
                "> `/disable_reminders` — Mute War or Raid pings (Admins)\n"
                "> `/botstatus` — View current server config\n"
                "> `/link` / `/unlink` — Connect/disconnect CoC tag to Discord"
            ),
            inline=False
        )
        full_embed.add_field(
            name="**Extras**",
            value=(
                "> `/flipcoin`\n"
                "> `/announce` — Make an announcement with the Dragon Bot\n"
                "> `/receiveposts` — Receive posts from Reddit; default subreddit is ClashOfClansLeaks\n"
                "> `/help` — This command"
            ),
            inline=False
        )

        full_embed.set_footer(text="Tip: Start with /setclantag and use /botstatus to setup your server!")

        view = HelpView(summary_embed, full_embed)
        await interaction.response.send_message(embed=summary_embed, view=view, ephemeral=True)

    # ... (rest of your commands like receive_posts, flipcoin, etc., stay below here) ...
    @app_commands.command(name="receiveposts", description="Receive posts from Reddit")
    @app_commands.describe(
        subreddit_name="The subreddit to check (Default: ClashOfClansLeaks)", 
        post_type="Choose: hot, new, or top", 
        limit="Number of posts (Max: 5)"
    )
    @app_commands.choices(post_type=[
        app_commands.Choice(name="Hot", value="hot"),
        app_commands.Choice(name="New", value="new"),
        app_commands.Choice(name="Top", value="top")
    ])
    # Set the default here in the argument list
    async def receive_posts(self, interaction: discord.Interaction, subreddit_name: str = "ClashOfClansLeaks", post_type: str = 'hot', limit: int = 3):
        await interaction.response.defer()
        
        try:
            subreddit = reddit.subreddit(subreddit_name) 
            
            # This triggers a check to see if the subreddit exists/is accessible
            try:
                subreddit.id 
            except Exception:
                return await interaction.followup.send(f"❌ Subreddit `r/{subreddit_name}` is private or does not exist.")

            limit = min(limit, 5) 

            # Fetching data
            if post_type == 'new':
                posts = subreddit.new(limit=12)
            elif post_type == 'top':
                posts = subreddit.top(limit=12)
            else:
                posts = subreddit.hot(limit=12)

            # Filter pinned and NSFW (optional but recommended for clan safety)
            non_pinned_posts = [post for post in posts if not post.stickied and not post.over_18][:limit]

            if not non_pinned_posts:
                return await interaction.followup.send(f"No suitable posts found in r/{subreddit_name}.")

            await interaction.followup.send(f"**{post_type.capitalize()} posts from r/{subreddit_name}:**")

            for post in non_pinned_posts: 
                # Convert Reddit Unix timestamp to a Discord-friendly integer
                post_time = int(post.created_utc)
                
                embed = discord.Embed(
                    title=post.title[:250],
                    url=f"https://reddit.com{post.permalink}", 
                    # Adding the relative timestamp to the description
                    description=f"Posted: <t:{post_time}:R>",
                    color=0xFF4500,
                    # This puts the exact date/time in the footer area
                    timestamp=datetime.fromtimestamp(post.created_utc)
                )
                
                # Image Logic
                if any(post.url.endswith(ext) for ext in ['.jpg', '.png', '.gif', '.jpeg']):
                    embed.set_image(url=post.url)
                elif post.thumbnail and post.thumbnail.startswith("http"):
                    embed.set_thumbnail(url=post.thumbnail)
                
                embed.set_footer(text=f"r/{subreddit_name} • 👍 {post.score} | 💬 {post.num_comments}")
                await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"⚠️ An unexpected error occurred: `{e}`")

    @app_commands.command(name="announce", description="Make an announcement")
    async def announce(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message(message)

    @app_commands.command(name="flipcoin", description="Flip coin (heads or tails)")
    async def flip(self, interaction: discord.Interaction):
        result = "Heads!!!" if random.randint(1, 2) == 1 else "Tails!!!"
        await interaction.response.send_message(f"The coin flips to... {result}")

    @app_commands.command(name="about", description="Information about Dragon Bot 2.0")
    async def about(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="About Dragon Bot 2.0",
            description="The ultimate companion for Clash of Clans leaders and players.",
            color=0x00ff00 # Or your brand color
        )

        # Main Info
        embed.add_field(name="Developer", value="Keepas", inline=True)
        embed.add_field(name="Website", value="[Visit Dashboard](https://dragon-bot-website.vercel.app/)", inline=True)

        
        embed.add_field(
            name="Legal",
            value=(
                "Dragon Bot 2.0 is an independent fan-made tool. "
                "It is not affiliated with, endorsed, or sponsored by Supercell. "
                "All game assets and trademarks belong to Supercell."
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="botstatus", description="Get the server configuration and status")
    async def server_status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(buffered=True)
            guild_id = str(interaction.guild.id)
            
            # 1. Fetch server configuration (clan tag, reminder channels)
            cursor.execute("SELECT clan_tag, war_channel_id, raid_channel_id FROM servers WHERE guild_id = %s", (guild_id,))
            row = cursor.fetchone()
            
            if row:
                # Keep the formatting clean, but show raw text if empty
                raw_clan_tag = row[0]
                clan_tag = f"`{raw_clan_tag}`" if raw_clan_tag else "`❌ Not Set`"
                war_mention = f"<#{row[1]}>" if row[1] else "`❌ Not Configured`"
                raid_mention = f"<#{row[2]}>" if row[2] else "`❌ Not Configured`"
            else:
                clan_tag = "`❌ Run /setclantag to configure`"
                war_mention = "`❌ Not Configured`"
                raid_mention = "`❌ Not Configured`"

            # 2. Fetch Linked Players globally, filtered to ONLY members of this server
            # We fetch all member IDs currently in this server guild
            member_ids = [str(member.id) for member in interaction.guild.members]
            players = []

            if member_ids:
                # Reconstruct an SQL "IN" clause: WHERE discord_id IN (%s, %s, %s...)
                placeholders = ','.join(['%s'] * len(member_ids))
                query = f"SELECT discord_username, player_tag FROM players WHERE discord_id IN ({placeholders})"
                
                cursor.execute(query, tuple(member_ids))
                players = cursor.fetchall()

            player_info = "\n".join([f"• @{u} (`{t}`)" for u, t in players]) if players else "` No Linked Members `"

            # 3. Build the Polished Embed
            embed = discord.Embed(
                title=f"🛡️ {interaction.guild.name} Configuration",
                color=0x3498db,
                timestamp=interaction.created_at
            )
            
            # Formatting correction: display clan_tag as string, not double backticks
            embed.add_field(name="Current Clan", value=clan_tag, inline=False)
            embed.add_field(name="⚔️ War Reminders", value=war_mention, inline=True)
            embed.add_field(name="🏰 Raid Reminders", value=raid_mention, inline=True)
            embed.add_field(name="Linked Members", value=player_info, inline=False)
            
            embed.set_footer(text=f"Serving {len(self.bot.guilds)} servers | {len(self.bot.users)} users")
            
            await interaction.followup.send(embed=embed)

            cursor.close()
            conn.close() # Always close the connection too!
        except Exception as e:
            print(f"Error in botstatus: {e}")
            import traceback
            traceback.print_exc()
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

    # --- STORE SESSION DATABASE HELPERS ---
    def _get_user_session(self, discord_id: str):
        """Fetches the registered Supercell Store cookie session for a Discord user."""
        # Reuses your existing get_db_connection helper!
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)
        try:
            cursor.execute(
                "SELECT cookies_json FROM coc_sessions WHERE discord_id = %s", 
                (discord_id,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            cursor.close()
            conn.close()

    def _save_user_session(self, discord_id: str, cookies_json: str):
        """Saves or updates a Discord user's cookie session."""
        # Reuses your existing get_db_connection helper!
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)
        try:
            query = """
                INSERT INTO coc_sessions (discord_id, cookies_json)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE 
                    cookies_json = VALUES(cookies_json)
            """
            cursor.execute(query, (discord_id, cookies_json))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    # --- UNIFIED INTERACTIVE LINK COMMAND ---
    @app_commands.command(name='link', description="Link your Clash of Clans account or Supercell Store.")
    async def link(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚔️ Clash of Clans Integration Menu",
            description=(
                "Choose an integration method below to link your profiles to the bot:\n\n"
                "**Link CoC Account:** Links your in-game profile to your Discord Account (requires playertag and API)\n"
                "**Link SuperCell Store :**Register your Supercell Store session for automatic reward collection!"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Manage your active profiles easily!")
        await interaction.response.send_message(embed=embed, view=LinkMenuView(self), ephemeral=True)

    # --- SECURE BACKGROUND COOKIE PROCESSOR ---
    async def handle_cookie_upload(self, interaction, user_id, target_channel=None):
        """Background loop waiting for the user to upload their cookie file privately in DMs."""
        def check(m):
            return m.author.id == user_id and m.guild is None and len(m.attachments) > 0

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=120.0)
            attachment = msg.attachments[0]
            
            file_bytes = await attachment.read()
            file_str = file_bytes.decode("utf-8")
            
            # Validate JSON list format
            parsed_cookies = json.loads(file_str)
            if not isinstance(parsed_cookies, list):
                raise ValueError("Cookie file must contain a JSON list of cookies.")

            self._save_user_session(str(user_id), file_str)

            success_text = "🎉 **Success!** Your Supercell Store session cookies are verified and linked securely. You can now type `/claim` in any server channel!"
            if target_channel:
                await target_channel.send(success_text)
            else:
                await msg.channel.send(success_text)

        except asyncio.TimeoutError:
            timeout_text = "⏰ **Timed Out:** You didn't upload your cookie file within 2 minutes. Click 'Link Store' in the server menu to try again!"
            if target_channel:
                await target_channel.send(timeout_text)
            else:
                await interaction.followup.send(timeout_text, ephemeral=True)
        except (json.JSONDecodeError, ValueError):
            err_text = "❌ **Registration Failed:** The uploaded file was not a valid exported JSON cookie list. Make sure your extension outputs in **JSON format** and try again!"
            if target_channel:
                await target_channel.send(err_text)
            else:
                await interaction.followup.send(err_text, ephemeral=True)
        except Exception as e:
            print(f"💥 System/DB Error loading session: {e}")
            err_text = f"❌ **System Error:** Failed to link your store profile: `{e}`"
            if target_channel:
                await target_channel.send(err_text)
            else:
                await interaction.followup.send(err_text, ephemeral=True)

    # --- UNIFIED GLOBAL UNLINK COMMAND ---
    @app_commands.command(name='unlink', description="Unlink your Clash of Clans account globally from the bot.")
    async def unlink(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            conn = get_db_connection()
            cursor = conn.cursor(buffered=True)
            
            # Deletes their global link mapping
            cursor.execute(
                "DELETE FROM players WHERE discord_id = %s", 
                (str(interaction.user.id),)
            )
            conn.commit()
            
            if cursor.rowcount > 0:
                await interaction.followup.send("✅ Your Clash of Clans account has been cleanly unlinked from the bot.")
            else:
                await interaction.followup.send("❌ You do not have an account linked to the bot.")
            
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"DB Error in Unlink: {e}")
            await interaction.followup.send("❌ An error occurred while unlinking.")

    # --- CLAIM COMMAND ---
    @app_commands.command(
        name="claim", 
        description="Manually claims rewards and checks mission progress for your registered account."
    )
    async def claim(self, interaction: discord.Interaction):
        print(f"\n📥 [Discord] /claim command triggered by {interaction.user.name}!")
        await interaction.response.defer(thinking=True)

        try:
            cookies_json_str = self._get_user_session(str(interaction.user.id))
            
            if not cookies_json_str:
                print(f"❌ [Discord] {interaction.user.name} is not registered.")
                embed = discord.Embed(
                    title="⚠️ Registration Required",
                    description=(
                        "You haven't linked a Supercell Store session to your Discord account yet!\n\n"
                        "**How to register:**\n"
                        "1. Run `/link` and click **Link Store (Cookies)**.\n"
                        "2. Drop your exported cookie file into your secure DM channel!"
                    ),
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed)
                return

            print(f"🚀 [Discord] Running Playwright worker for {interaction.user.name}...")
            data = await run_mission_worker(str(interaction.user.id), cookies_json_str)
            print("🛰️ [Discord] Playwright worker finished execution.")

            if not data.get("success", False):
                error_msg = data.get("error", "Unknown Error")
                print(f"❌ [Discord] Worker failed: {error_msg}")
                embed = discord.Embed(
                    title="⚠️ Claim Failed",
                    description=f"Reason: `{error_msg}`\n\nIf your session expired, run `/link` and update your store cookies again.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            claimed_rewards = data["claimed"]
            embed = discord.Embed(
                title="Store Claim Status",
                description=f"Successfully claimed **{claimed_rewards}** rewards!",
                color=discord.Color.green() if claimed_rewards > 0 else discord.Color.gold()
            )

            if data.get("missions"):
                for mission in data["missions"]:
                    is_completed = "COMPLETED" in mission["progress"].upper()
                    status_emoji = "✅" if is_completed else "⏳"
                    
                    embed.add_field(
                        name=f"{status_emoji} {mission['title']}",
                        value=f"Progress: `{mission['progress']}` | Reward: `{mission['reward']}`",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="ℹ️ No Missions Found",
                    value="Could not parse any active missions right now.",
                    inline=False
                )

            embed.set_footer(text="Keep Clashing, Chief! ⚔️")
            await interaction.followup.send(embed=embed)
            print("✅ [Discord] Embed successfully sent to user.")

        except Exception as e:
            print(f"💥 [Discord] CRITICAL ERROR in slash command execution: {e}")
            try:
                await interaction.followup.send(f"⚠️ A critical error occurred inside the bot: `{e}`")
            except Exception:
                pass


    
    @app_commands.command(name="disable_reminders", description="Turn off specific background reminders")
    @app_commands.describe(type="Choose which reminder to disable")
    @app_commands.choices(type=[
        app_commands.Choice(name="⚔️ War Reminders", value="war"),
        app_commands.Choice(name="🏰 Raid Reminders", value="raid"),
        app_commands.Choice(name="🚫 Both", value="both")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def disable_reminders(self, interaction: discord.Interaction, type: str):
        await interaction.response.defer(ephemeral=True)
        
        cursor = get_db_cursor()
        guild_id = str(interaction.guild.id)
        
        if type == "war":
            sql = "UPDATE servers SET war_channel_id = NULL WHERE guild_id = %s"
            label = "⚔️ War Reminders"
        elif type == "raid":
            sql = "UPDATE servers SET raid_channel_id = NULL WHERE guild_id = %s"
            label = "🏰 Raid Reminders"
        else:
            sql = "UPDATE servers SET war_channel_id = NULL, raid_channel_id = NULL WHERE guild_id = %s"
            label = "⚔️ War and 🏰 Raid Reminders"

        try:
            cursor.execute(sql, (guild_id,))
            # commit is usually handled inside get_db_cursor or at the end of execution
            
            await interaction.followup.send(f"✅ {label} have been disabled for this server.")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to update settings: {e}")

    # Ensure you have 'import praw' at the top of your file!
    # The reddit instance should be initialized in your __init__ or globally
    
async def setup(bot):
    await bot.add_cog(BotCommands(bot))