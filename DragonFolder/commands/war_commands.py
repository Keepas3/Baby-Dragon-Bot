import discord
import time
import re
import coc
from discord.ext import commands
from discord import app_commands, Embed
# import traceback
#traceback.print_exc() # This prints the EXACT line causing the error in your terminal
# Import helpers from your toolbox
from config import get_db_cursor, coc_client
from utils import (
    fetch_clan_from_db, get_current_war_data, get_war_log_data,
    get_cwl_data, format_datetime, format_month_day_year, ClanNotSetError
)

class WarCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="currentwar", description="Get general info or member stats for current war (normal or CWL)")
    @app_commands.describe(wartag="Tag for a specific CWL war", mode="info or stats")
    async def currentwar(self, interaction: discord.Interaction, wartag: str = None, mode: str = "info"):
        """Displays status or detailed attack stats for the active war."""
        cursor = get_db_cursor()
        guild_id = interaction.guild.id
        
        # 1. Fetch tag from DB
        try:
            db_tag = fetch_clan_from_db(guild_id)
        except ClanNotSetError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)

        await interaction.response.defer()

        try:
            # 2. Fetch data via helper
            war_data = await get_current_war_data(db_tag, wartag)
            
            if not war_data or war_data.get('state') == 'notInWar':
                return await interaction.followup.send("The clan is not currently in a war.")

            is_cwl = bool(wartag)
            source = "CWL" if is_cwl else "Normal"
            clanA, clanB = war_data.get("clan", {}), war_data.get("opponent", {}),

            def clean(t): return t.strip().lstrip("#").upper()
            if is_cwl and clean(clanA.get("tag", "")) != clean(db_tag):
                our_block, opp_block = clanB, clanA
            else:
                our_block, opp_block = clanA, clanB

            attacks = our_block.get("attacks", 0)
            total_attacks = our_block.get("total_attacks", 0)

            # MODE: General Info (Embed)
            if mode.lower() == "info":
                state = war_data.get("state", "Unknown")
                clan_stars, opp_stars = our_block.get("stars", 0), opp_block.get("stars", 0)
                
                embed = Embed(
                    title=f"{our_block.get('name','?')} vs {opp_block.get('name','?')}",
                    description=f"{source} War — State: :crossed_swords: {state}\nLast Updated: <t:{int(time.time())}:R>",
                    color=0x00ff00 if clan_stars > opp_stars else 0xff0000 if clan_stars < opp_stars else 0xffff00
                )
                
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

    @app_commands.command(name="cwlschedule", description="Receive information about the current CWL Schedule")
    async def cwlschedule(self, interaction: discord.Interaction):
        """Fetches the rounds and opponents for the current CWL season."""
        DEFAULT_CLAN_TAG = "#2JL28OGJJ"
        cursor = get_db_cursor()
        guild_id = interaction.guild.id
        
        cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
        row = cursor.fetchone()
        raw_tag = row[0] if row and row[0] else DEFAULT_CLAN_TAG

        await interaction.response.defer()

        try:
            group = await coc_client.get_league_group(raw_tag)
            
            if not group:
                return await interaction.followup.send("This clan is not participating in CWL right now.")

            lines = [
                f"**CWL Season {group.season}** -  State: {group.state}",
                "",
                "Participating Clans:"
            ]
            for i, c in enumerate(group.clans, start=1):
                lines.append(f"{i}. {c.name} ({c.tag}) – Level {c.level}")

            lines.append("\nRound Schedule:")
            my_norm = raw_tag.strip().lstrip("#").upper()

            for idx, round_data in enumerate(group.rounds, start=1):
                opponent_name = None
                found_war_tag = None

                for wt in round_data.war_tags:
                    if wt == "#0": continue
                    war = await coc_client.get_league_war(wt)
                    if not war: continue

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

    @app_commands.command(name="warlog", description="Retrieve the clan's war log")
    async def war_log(self, interaction: discord.Interaction, limit: int = 1):
        await interaction.response.defer()
        try:
            tag = fetch_clan_from_db(interaction.guild.id)
            war_log = await get_war_log_data(tag)
            
            if not war_log:
                return await interaction.followup.send("No public war log found or log is private.")

            count = 0
            # We iterate directly to avoid the slicing bug in coc.py
            for entry in war_log:
                if count >= limit:
                    break
                
                # Check for CWL entries
                is_cwl = getattr(entry, 'is_league_entry', False)
                
                # Safely handle names and stars
                clan_name = entry.clan.name
                if entry.opponent:
                    opp_name = entry.opponent.name
                    opp_stars = entry.opponent.stars
                else:
                    opp_name = "CWL Opponent"
                    opp_stars = "?"

                res_raw = str(entry.result).lower() if entry.result else "league"
                color = 0x00ff00 if "win" in res_raw else 0xff0000 if "lose" in res_raw else 0xffff00

                embed = discord.Embed(
                    title=f"{clan_name} vs {opp_name}",
                    description=f"Type: {'CWL' if is_cwl else 'Normal War'}\nEnd: {format_month_day_year(entry.end_time)}",
                    color=color
                )
                embed.add_field(name="Stars", value=f"{entry.clan.stars} - {opp_stars}", inline=True)
                embed.add_field(name="Destruction", value=f"{round(entry.clan.destruction, 1)}%", inline=True)
                
                await interaction.followup.send(embed=embed)
                count += 1

        except Exception as e:
            # This handles the internal library crash gracefully
            await interaction.followup.send(f"An entry in the war log could not be parsed by the library: {e}")

            
    @app_commands.command(name="cwlclansearch", description="Search CWL clans by name or tag")
    @app_commands.describe(nameortag="Clan name or tag")
    async def cwlclansearch(self, interaction: discord.Interaction, nameortag: str):
        """Searches for a specific clan within the current CWL group."""
        DEFAULT_CLAN_TAG = "#2JL28OGJJ"
        cursor = get_db_cursor()
        guild_id = interaction.guild.id
        
        cursor.execute("SELECT clan_tag FROM servers WHERE guild_id = %s", (guild_id,))
        row = cursor.fetchone()
        raw_tag = row[0] if row and row[0] else DEFAULT_CLAN_TAG

        query = nameortag.strip().upper()
        is_tag = query.startswith("#") or re.fullmatch(r"[0-9A-Z]+", query)

        await interaction.response.defer()

        try:
            current_war = await coc_client.get_current_war(raw_tag)
            
            if not current_war or current_war.state == "notInWar":
                return await interaction.followup.send("This clan is not in a CWL war right now.")

            group = await coc_client.get_league_group(raw_tag)
            clans = group.clans if group else []
            state = "Preparation" if current_war.state == "preparation" else (group.state if group else "Unknown")

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

            full_clan = await coc_client.get_clan(match.tag)
            sorted_m = sorted(full_clan.members, key=lambda m: m.town_hall, reverse=True)

            member_info = "\n".join(f"{i}. {m.name} (TH {m.town_hall})" for i, m in enumerate(sorted_m, start=1))

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

# Requirement for main.py loading
async def setup(bot):
    await bot.add_cog(WarCommands(bot))