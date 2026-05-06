# src/commands/claim_commands.py
import discord
from discord import app_commands
from discord.ext import commands
from src.services.coc_worker import run_mission_worker

class ClaimCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="claim", 
        description="Manually claims Supercell Store rewards and grabs current mission progress."
    )
    async def claim(self, interaction: discord.Interaction):
        # 1. Defer immediately. Playwright takes ~10-15 seconds to run, 
        # and Discord commands will time out and error after 3 seconds without this.
        await interaction.response.defer(thinking=True)

        # 2. Run the Playwright service in the background
        data = await run_mission_worker()

        # 3. Handle a login expiration or scraping failure
        if not data["success"]:
            embed = discord.Embed(
                title="⚠️ Claim Attempt Failed",
                description=f"Reason: `{data.get('error', 'Unknown Error')}`",
                color=discord.Color.red()
            )
            embed.set_footer(text="Try running auth_manager.py again if your session expired.")
            await interaction.followup.send(embed=embed)
            return

        # 4. Handle a successful claim run
        claimed_rewards = data["claimed"]
        embed = discord.Embed(
            title="🛡️ Supercell Store Claim Status",
            description=f"Successfully claimed **{claimed_rewards}** rewards! Log into Clash of Clans to verify.",
            color=discord.Color.green() if claimed_rewards > 0 else discord.Color.gold()
        )

        # 5. Loop through and dynamically build your mission list
        if data["missions"]:
            for mission in data["missions"]:
                # Use a green checkmark if completed, otherwise a progress timer
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

async def setup(bot: commands.Bot):
    await bot.add_cog(ClaimCommands(bot))