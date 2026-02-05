import discord
import asyncio
import coc
from discord.ext import commands, tasks
from discord import app_commands, Embed
from config import get_db_cursor, coc_client
from utils import (
    fetch_clan_from_db, get_current_war_data, get_war_log_data,
    get_cwl_data, format_datetime, format_month_day_year, ClanNotSetError,
    check_coc_clan_tag  # Ensure this is imported for setclantag!
)

class WarCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="currentwar", description="Get info or member stats for current war")
    @app_commands.describe(wartag="Tag for a specific CWL war", mode="info or stats")
    async def currentwar(self, interaction: discord.Interaction, wartag: str = None, mode: str = "info"):
    
        import asyncio
        import time
        coc_client.loop = asyncio.get_running_loop()

        await interaction.response.defer()
        
        try:
            db_tag = fetch_clan_from_db(interaction.guild.id)
            war_data = None
            
            # 1. Fetch the data
            if wartag:
                war_data = await coc_client.get_league_war(wartag)
            else:
                # Standard check
                war_data = await coc_client.get_current_war(db_tag)
                
                # If standard check is empty or not in war, try the group
                if not war_data or war_data.state == "notInWar":
                    group = await coc_client.get_league_group(db_tag)
                    if group:
                        async for war in group.get_wars_for_clan(db_tag):
                            if war.state != "notInWar":
                                war_data = war
                                break

            if not war_data or war_data.state == "notInWar":
                return await interaction.followup.send("No active war or CWL round found.")

            # --- DYNAMIC TYPE DETECTION ---
            # We check if it's CWL by looking for league-specific properties
            is_cwl = getattr(war_data, 'is_league_entry', False) or hasattr(war_data, 'war_tag')
            source = "CWL" if is_cwl else "Normal War"

            # Ensure our clan is always 'our'
            if war_data.clan.tag == db_tag:
                our, opp = war_data.clan, war_data.opponent
            else:
                our, opp = war_data.opponent, war_data.clan

            # 2. Format the Embed
            max_attacks = 1 if is_cwl else 2
            total_possible = war_data.team_size * max_attacks
            if mode.lower() == "info":
                display_state = str(war_data.state).capitalize()
                
                # Determine color based on stars
                if our.stars > opp.stars: embed_color = 0x00ff00 # Green
                elif our.stars < opp.stars: embed_color = 0xff0000 # Red
                else: embed_color = 0xffff00 # Yellow

                embed = discord.Embed(
                    title=f"{our.name} vs {opp.name}",
                    description=f"**Type:** {source}\n**State:** {display_state}",
                    color=embed_color
                )
                
                # Add extra info for CWL like the Round number if available
                if is_cwl and hasattr(war_data, 'war_tag'):
                    embed.set_footer(text=f"CWL War Tag: {war_data.war_tag}")

                embed.add_field(name="Clan Stars", value=f"⭐ {our.stars}/{our.max_stars}", inline=True)
                embed.add_field(name="Clan Attacks Used", value=f"`{our.attacks_used}/{total_possible}`", inline=True)
                embed.add_field(name="Clan Destruction", value=f"💥 {round(our.destruction, 1)}%/100%", inline=True)

                # embed.add_field(name="Stars", value=f"⭐ {our.stars} - {opp.stars}", inline=True)
                # embed.add_field(name="Destruction", value=f"💥 {round(our.destruction, 1)}% - {round(opp.destruction, 1)}%", inline=True)
                
                embed.add_field(name="Clan Stars", value=f"⭐ {opp.stars}/{opp.max_stars}", inline=True)
                embed.add_field(name="Clan Attacks Used", value=f"`{opp.attacks_used}/{total_possible}`", inline=True)
                embed.add_field(name="Clan Destruction", value=f"💥 {round(opp.destruction, 1)}%/100%", inline=True)

                # CWL has 1 attack per person, Normal has 2
                atks_per_person = 1 if is_cwl else 2
                total_atks = war_data.team_size * atks_per_person
                embed.add_field(name="Attacks", value=f"⚔️ {our.attacks_used} / {total_atks}", inline=False)
                
                await interaction.followup.send(embed=embed)
                # --- STATS MODE (YAML) ---
            elif mode.lower() == "stats":
                
                # coc.py Clan objects have a 'members' attribute
                members = our.members 

                attacked, unattacked = [], []
                
                for m in members:
                    # m.attacks is a list of WarAttack objects
                    atks = m.attacks 
                    
                    entry = {
                        "name": m.name,
                        "th": m.town_hall,
                        "stars": sum(a.stars for a in atks),
                        "pct": sum(a.destruction for a in atks),
                        "att": len(atks)
                    }
                    
                    if entry["att"] > 0:
                        attacked.append(entry)
                    else:
                        unattacked.append(entry)

                # Sorting: Top performers first, then highest THs for those who haven't hit
                attacked.sort(key=lambda e: (e["stars"], e["pct"]), reverse=True)
                unattacked.sort(key=lambda e: (e["th"], e["name"]), reverse=True)

                # Build the text lines
                display_state = str(war_data.state).capitalize()

                
                lines = [
                    f"```yaml",
                    f"{source} War Stats — {our.name}",
                    f"State: {display_state}",
                    f"Total Attacks Used: {our.attacks_used} / {total_possible}",
                    ""
                ]

                if attacked:
                    lines.append("✅ Attacked")
                    for i, e in enumerate(attacked, 1):
                        lines.append(f"{i}. {e['name']}: {e['stars']}⭐, {round(e['pct'], 1)}% ({e['att']}/{max_attacks})")
                
                if unattacked:
                    lines.append("\n❌ Not Attacked")
                    for i, e in enumerate(unattacked, 1):
                        lines.append(f"{i}. {e['name']}: TH{e['th']} (0/{max_attacks})")
                
                lines.append("```")

                # Join lines and send (Discord has a 2000 character limit)
                final_yaml = "\n".join(lines)
                if len(final_yaml) > 2000:
                    # If too long, send in two chunks
                    half = len(lines) // 2
                    await interaction.followup.send("\n".join(lines[:half]) + "```")
                    await interaction.followup.send("```yaml\n" + "\n".join(lines[half:]))
                else:
                    await interaction.followup.send(final_yaml)
            # --- MISSED ATTACKS MODE ---
            elif mode.lower() == "missed":
                max_atks = 1 if is_cwl else 2
                missed_list = []

                for m in our.members:
                    if len(m.attacks) < max_atks:
                        # We calculate how many they actually missed
                        count = max_atks - len(m.attacks)
                        missed_list.append(f"- {m.name} (Missed {count})")

                if not missed_list:
                    return await interaction.followup.send("Everyone used all their attacks.")

                header = f"**Missed Attacks: {source} War vs {opp.name}**"
                body = "\n".join(missed_list)
                await interaction.followup.send(f"{header}\n{body}")

        except Exception as e:
            await interaction.followup.send(f"Error: {e}")

    @app_commands.command(name="cwlschedule", description="Receive information about the current CWL Schedule")
    async def cwlschedule(self, interaction: discord.Interaction):
        """Fetches the rounds and opponents for the current CWL season."""
        DEFAULT_CLAN_TAG = "#2JL28OGJJ"
        guild_id = interaction.guild.id
        
        try:
            db_tag = fetch_clan_from_db(guild_id)
        except ClanNotSetError:
            db_tag = DEFAULT_CLAN_TAG

        await interaction.response.defer()

        try:
            # 1. Fetch the group first
            group = await coc_client.get_league_group(db_tag)
            
            if not group:
                return await interaction.followup.send("This clan is not participating in CWL right now.")

            lines = [
                f"**CWL Season {group.season}** - State: {group.state}",
                "",
                "Participating Clans:"
            ]
            for i, c in enumerate(group.clans, start=1):
                lines.append(f"{i}. {c.name} ({c.tag})")

            lines.append("\nRound Schedule:")

            # 2. TO FIX THE LOOP ERROR: 
            # We will fetch wars manually but in a simplified way that doesn't trigger 
            # the library's internal loop conflict.
            my_norm = db_tag.strip().lstrip("#").upper()
            
            # Instead of the Iterator, we fetch only the rounds that have valid tags
            for idx, round_tags in enumerate(group.rounds, start=1):
                opponent_name = "Not yet scheduled"
                
                # Filter out the empty #0 tags before making requests
                valid_tags = [t for t in round_tags if t != "#0"]
                
                if not valid_tags:
                    lines.append(f"Round {idx}: {opponent_name}")
                    continue

                # Look for our clan in the round's wars
                found = False
                for wt in valid_tags:
                    try:
                        # Fetch the specific war
                        war = await coc_client.get_league_war(wt)
                        
                        # Check if our clan is in this war
                        c1 = war.clan.tag.strip().lstrip("#").upper()
                        c2 = war.opponent.tag.strip().lstrip("#").upper()
                        
                        if c1 == my_norm:
                            opponent_name = f"vs {war.opponent.name}"
                            found = True
                        elif c2 == my_norm:
                            opponent_name = f"vs {war.clan.name}"
                            found = True
                        
                        if found:
                            lines.append(f"Round {idx}: {opponent_name} (War Tag: {wt})")
                            break
                    except Exception:
                        continue # Skip failed fetches
                
                if not found:
                    lines.append(f"Round {idx}: {opponent_name}")

            text = "```yaml\n" + "\n".join(lines) + "\n```"
            await interaction.followup.send(text)

        except Exception as e:
            # If the loop error still persists, we know it's the coc_client initialization
            print(f"DEBUG: {e}")
            await interaction.followup.send(f"Error: {e}")

    @app_commands.command(name="warlog", description="Retrieve the clan's war log")
    @app_commands.describe(limit="Number of recent wars to display (max 8)")
    async def war_log(self, interaction: discord.Interaction, limit: int = 1):
        await interaction.response.defer()
        try:
            tag = fetch_clan_from_db(interaction.guild.id)
            war_log = await get_war_log_data(tag)
            
            if not war_log:
                return await interaction.followup.send("No public war log found or log is private.")

            count = 0
            # We iterate directly to avoid the slicing bug in coc.py
            limit = max(1, min(limit, 8)) 
            for entry in war_log:
                if count >= limit:
                    break
                is_cwl = getattr(entry, 'is_league_entry', False)
                max_atks_per_player = 1 if is_cwl else 2
                
                total_possible = entry.team_size * max_atks_per_player
                
                # Safely handle names and stars
                clan_name = entry.clan.name
                clan_tag = entry.clan.tag
                clan_stars = entry.clan.stars
                if entry.opponent:
                    opp_name = entry.opponent.name
                    opp_tag =  entry.opponent.tag
                    
                else:
                    opp_name = "CWL"
                    opp_stars = "__"
                
                CWL_rounds = 7
                clan_destruction = round(entry.clan.destruction, 2)
                opp_destruction = round(entry.opponent.destruction, 2) if entry.opponent else 0

                res_raw = str(entry.result).lower() if entry.result else "league"
                color = 0x00ff00 if "win" in res_raw else 0xff0000 if "lose" in res_raw else 0xffff00

                embed = discord.Embed(
                    title=f"{clan_name} vs {opp_name}",
                    description=f"Type: {'CWL' if opp_name == '' else 'Normal War'}\nClan Tag: `{clan_tag}` | Opp. Tag: `{opp_tag}`",
                    color=color
                )
                embed.add_field(name="Result", value=f"**{entry.result}**", inline=False)

                if is_cwl:
                    embed.add_field(name="Clan Stars", value=f":star: {entry.clan.stars}/{entry.clan.max_stars*7}", inline=True)
                    embed.add_field(name="Clan Attacks Used", value=f"`{entry.clan.attacks_used}/{total_possible*7}`", inline=True)
                    embed.add_field(name="Clan Destruction", value=f":fire: {clan_destruction}%/700%", inline=True)
                if not is_cwl:
                    embed.add_field(name="Clan Stars", value=f":star: {entry.clan.stars}/{(entry.clan.max_stars)}", inline=True)
                    embed.add_field(name="Clan Attacks Used", value=f"`{entry.clan.attacks_used}`/`{total_possible}`", inline=True)
                    embed.add_field(name="Clan Destruction", value=f":fire: {clan_destruction}%/100%", inline=True)
                if not is_cwl:
                    embed.add_field(name="Opponent Stars", value=f":star: {entry.opponent.stars}/{entry.opponent.max_stars}", inline=True)
                    embed.add_field(name="Opponent Attacks Used", value=f"`{entry.opponent.attacks_used}`/`{total_possible}`", inline=True)
                    embed.add_field(name="Opponent Destruction", value=f":fire: {opp_destruction}%/100%", inline=True)

                # embed.add_field(name="Stars", value=f"{entry.clan.stars} - {opp_stars}", inline=True)
                # embed.add_field(name="Destruction", value=f"{round(entry.clan.destruction, 1)}%", inline=True)
                embed.add_field(name = "Exp. Earned", value=f"{entry.clan.exp_earned}", inline=False)
                end_date = format_month_day_year(entry.end_time)
                embed.add_field(name="End Date", value=end_date, inline=False)
                
                await interaction.followup.send(embed=embed)
                count += 1

        except Exception as e:
            # This handles the internal library crash gracefully
            await interaction.followup.send(f"An entry in the war log could not be parsed by the library: {e}")

            
    @app_commands.command(name="cwlclansearch", description="Search CWL clans by name or tag")
    @app_commands.describe(nameortag="Clan name or tag")
    async def cwlclansearch(self, interaction: discord.Interaction, nameortag: str):
        await interaction.response.defer()
        try:
            db_tag = fetch_clan_from_db(interaction.guild.id)
            group = await coc_client.get_league_group(db_tag)
            
            if not group:
                return await interaction.followup.send("This clan is not participating in CWL right now.")

            query = nameortag.strip().upper().lstrip("#")
            match_tag = None

            # 1. First, search the group.clans list (if populated)
            for clan in group.clans:
                if clan.tag.lstrip("#").upper() == query or clan.name.upper() == query:
                    match_tag = clan.tag
                    break

            # 2. If not found and Round 1 has tags, search the actual wars
            # This is helpful if group.clans is empty during Round 1 prep
            if not match_tag and group.rounds:
                # Check Round 1 (index 0)
                round_one_tags = [t for t in group.rounds[0] if t != "#0"]
                for wt in round_one_tags:
                    try:
                        war = await coc_client.get_league_war(wt)
                        # Check Clan A
                        if war.clan.tag.lstrip("#").upper() == query or war.clan.name.upper() == query:
                            match_tag = war.clan.tag
                            break
                        # Check Clan B
                        if war.opponent.tag.lstrip("#").upper() == query or war.opponent.name.upper() == query:
                            match_tag = war.opponent.tag
                            break
                    except:
                        continue
                    if match_tag: break

            if not match_tag:
                return await interaction.followup.send(
                    f"Clan `{nameortag}` not found. If CWL just started, the API may take a few minutes to sync all clans."
                )

            # 3. Final Fetch
            full_clan = await coc_client.get_clan(match_tag)
            sorted_m = sorted(full_clan.members, key=lambda m: m.town_hall, reverse=True)
            member_info = "\n".join(f"{i}. {m.name} (TH {m.town_hall})" for i, m in enumerate(sorted_m[:30], start=1))

            res = (
                f"```yaml\n"
                f"CWL Clan Search Result\n"
                f"Status: {group.state}\n"
                f"Clan: {full_clan.name} ({full_clan.tag})\n"
                f"TH Breakdown (Top 30):\n"
                f"{member_info}\n"
                f"```"
            )
            await interaction.followup.send(res)

        except Exception as e:
            await interaction.followup.send(f"Error: {e}")
            
    @app_commands.command(name="cwlprep", description="Full scout of enemy TH levels and Win Streaks")
    async def cwl_prep(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            db_tag = fetch_clan_from_db(interaction.guild.id)
            group = await coc_client.get_league_group(db_tag)
            
            if not group:
                return await interaction.followup.send("No active CWL group found.")

            lines = [f"**CWL Scouting: Season {group.season}**", ""]
            
            for clan in group.clans:
                # 1. Fetch clan data
                clan_obj = await coc_client.get_clan(clan.tag)
                
                # 2. Count ALL Town Halls
                th_counts = {}
                for m in clan_obj.members:
                    th_counts[m.town_hall] = th_counts.get(m.town_hall, 0) + 1
                
                # 3. Format the full breakdown (Sorted highest TH to lowest)
                # This creates a string like: "TH16: 5, TH15: 12, TH14: 3..."
                all_ths = ", ".join([f"TH{th}: {count}" for th, count in sorted(th_counts.items(), reverse=True)])
                
                # 4. War Streak logic
                streak = clan_obj.war_win_streak
                streak_emoji = "🔥" if streak >= 5 else "⚔️"
                
                # 5. Public/Private log indicator
                log_status = "🔓 Public Log" if clan_obj.public_war_log else "🔒 Private Log"

                lines.append(f"{clan_obj.name} (Lvl {clan_obj.level})")
                lines.append(f"  Streak: {streak_emoji} {streak} Wins | {log_status}")
                lines.append(f"  Lineup: {all_ths}")
                lines.append("-" * 25)

            # 6. Final Formatting and character limit safety
            final_msg = "```yaml\n" + "\n".join(lines) + "```"
            
            if len(final_msg) > 2000:
                # Split the message if it's too long for Discord
                chunks = [final_msg[i:i+1990] for i in range(0, len(final_msg), 1990)]
                for chunk in chunks:
                    await interaction.followup.send(chunk if chunk.startswith("```") else f"```yaml\n{chunk}")
            else:
                await interaction.followup.send(final_msg)

        except Exception as e:
            await interaction.followup.send(f"Scouting Error: {e}")

class WarPatrol(commands.Cog):
    def __init__(self, bot, coc_client):
        self.bot = bot
        self.coc_client = coc_client
        self.war_reminder.start()

    def cog_unload(self):
        self.war_reminder.cancel()

    @tasks.loop(minutes=20)
    async def war_reminder(self):
        """Background task to check all linked clans for pending attacks."""
        
        
        try:
            cursor = get_db_cursor()
            # 1. Pull the specific reminder channel for EACH server
            cursor.execute("SELECT clan_tag, guild_id, war_channel_id FROM servers")
            tracked_clans = cursor.fetchall()

            for clan_tag, guild_id, war_channel_id in tracked_clans:
                if not clan_tag or not war_channel_id:
                    continue # Skip servers that haven't run /setclantag yet

                try:
                    # 2. Fetch war data (Normal or CWL)
                    war = await self.coc_client.get_current_war(clan_tag)
                    
                    # If not in normal war, check if it's CWL
                    if not war or war.state == "notInWar":
                        group = await self.coc_client.get_league_group(clan_tag)
                        if group and group.state != "ended":
                            async for cwl_war in group.get_wars_for_clan(clan_tag):
                                if cwl_war.state == "inWar":
                                    war = cwl_war
                                    break
                    
                    if not war or war.state != "inWar":
                        continue

                    # 3. Check time remaining
                    seconds_left = war.end_time.seconds_until
                    
                    # Logic: Only ping if exactly ~4 hours or ~1 hour left
                    # (Adjusted range to catch the 30-minute loop interval)
                    is_final_call = 1800 <= seconds_left <= 3600    # 30-60 mins left
                    is_warning = 12600 <= seconds_left <= 14400     # 3.5-4 hours left

                    if not (is_final_call or is_warning):
                        continue

                    # 4. Identify Slackers
                    is_cwl = getattr(war, 'is_league_entry', False)
                    max_atks = 1 if is_cwl else 2
                    slacking_names = []
                    
                    for m in war.clan.members:
                        if len(m.attacks) < max_atks:
                            needed = max_atks - len(m.attacks)
                            slacking_names.append(f"• **{m.name}** ({needed} left)")

                    if not slacking_names:
                        continue 

                    # 5. POST TO THE SAVED CHANNEL
                    # We convert war_channel_id back to int because it's stored as CHAR/String
                    channel = self.bot.get_channel(int(war_channel_id))
                    if not channel:
                        continue

                    time_label = "FINAL HOUR" if is_final_call else "4 HOURS LEFT"
                    
                    embed = discord.Embed(
                        title=f"⚔️ {time_label}: War Attack Reminder",
                        description=f"Clan: **{war.clan.name}** vs **{war.opponent.name}**\n"
                                    f"Please use your remaining hits before the war ends!",
                        color=0xff0000 if is_final_call else 0xffa500
                    )
                    embed.add_field(name="Pending Attacks", value="\n".join(slacking_names))
                    embed.set_footer(text=f"War Type: {'CWL' if is_cwl else 'Normal War'}")
                    
                    await channel.send(embed=embed)

                except Exception as e:
                    print(f"Task Error for {clan_tag}: {e}")

        except Exception as db_e:
            print(f"Database Task Error: {db_e}")

    @war_reminder.before_loop
    async def before_war_reminder(self):
        await self.bot.wait_until_ready()

# --- CRITICAL SETUP UPDATE ---
async def setup(bot):
    # This adds the slash commands
    await bot.add_cog(WarCommands(bot))
    # This adds the background reminder task
    await bot.add_cog(WarPatrol(bot, coc_client))