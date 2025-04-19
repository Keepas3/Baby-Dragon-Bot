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

TOKEN = os.getenv('DISCORD_TOKEN2')
api_key = os.getenv('COC_api_key')
clan_tag = '#2QQ2VCU82'.replace('#', '%23')
og_clan_tag = '#2QQ2VCU82'


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix = "!", intents= intents)


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

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'logged in as {bot.user}!')

@bot.tree.command(name = "stats", description = "Stats of the bot") #guild = GUILD_ID
async def stats(interaction: discord.Interaction):
    server_count =len(bot.guilds)
    user_count = len(bot.users)
    stats_message = (
        f"**Bot Statistics**\n" 
        f"Servers: {server_count}\n" 
        f"Users: {user_count}\n"
    )
    print(f"Sending stats: {stats_message}") # Debugging print statement
    await interaction.response.send_message(stats_message)

@bot.tree.command(name="flipcoin", description="Flip coin (heads or tails)")
async def flip(interaction: discord.Interaction):
    integer1 = random.randint(1,2)
    if integer1 == 1:
        await interaction.response.send_message("The coin flips to... Heads!!!")
    elif integer1 == 2:
        await interaction.response.send_message("The coin flips to... Tails!!!")

def check_coc_clan_tag(clan_tag): 
  #  api_key = 'YOUR_API_KEY'
    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}' 
    headers = { 'Authorization': f'Bearer {api_key}', 'Accept': 'application/json' } 
    response = requests.get(url, headers=headers) 
    if response.status_code == 200: 
        return True # Valid clan tag 
    elif response.status_code == 404: 
        return False

@bot.tree.command(name = 'setclantag')
#@app_commands.checks.has_any_role("Admin", "Co-Leaders", "Elders")
async def set_clan_tag(interaction: discord.Interaction, new_tag: str):
    if check_coc_clan_tag(new_tag.replace('#', '%23')):
        global clan_tag
        clan_tag = new_tag.replace('#', '%23')
        await interaction.response.send_message(f'Clan tag has been updated to {new_tag}')
    else:
        await interaction.response.send_message(f"Not a valid Clan ID") 

@set_clan_tag.error 
async def set_clan_tag_error(interaction: discord.Interaction, error): 
    if isinstance(error, app_commands.MissingRole): 
        await interaction.response.send_message("You don't have permission to use this command.") 
    else:
        await interaction.response.send_message(f"An error occurred: {error}")                  
          
# @bot.tree.command(name = "clean", description ='Clean messages from the bot')
# async def clean(interaction : discord.Interaction, limit: int =2):
#     await interaction.response.defer()
#     if limit < 2 or limit >10:
#         limit = 2
#     deleted = await interaction.channel.purge(limit =limit)
#     await interaction.followup.send(f"Deleted {len(deleted)} messages")


    

@bot.tree.command(name="playerinfo", description="Get player's general information")
async def player_info(interaction: discord.Interaction, player_tag: str):
    player_tag = player_tag.replace('#', '%23')
    if not api_key:
        raise ValueError("API KEY NOT FOUND")

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

        # Create a Discord Embed object
        if role == 'admin':
            role = "Elder"
        elif role == 'coLeader':
            role = "Co-Leader"
        elif role == 'leader':
            role = "Leader"
        elif role == 'member':
            role == "Member"
        
        
        embed = discord.Embed(

            title=f"User: {player_name}, {player_data['tag']}",
            description=filtered_labels if filtered_labels else 'None',
            # url=f"https://www.clashofstats.com/players/{player_name}-{player_tag}/summary",
            color=0x0000FF  # Set an aesthetic color for the embed
        )
        embed.set_thumbnail(url=player_data['league']['iconUrls']['small'])
        embed.add_field(name="Clan Name", value=player_data['clan']['name'], inline=True)
        embed.add_field(name="Tag", value=player_data['clan']['tag'], inline=True)
        embed.add_field(name="Role", value=role, inline=True)

        embed.add_field(name="TH Lvl", value=player_data['townHallLevel'], inline=True)
        embed.add_field(name="Exp Lvl", value=player_data['expLevel'], inline=True)
        if preference == 'in':
            embed.add_field(name="War Preference", value=f":white_check_mark: {preference}", inline=True)
        elif preference == 'out':
            embed.add_field(name="War Preference", value=f":x: {preference}", inline=True)
        
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
@app_commands.describe(player_tag="The user's tag", village="The type of village: home, builder or both")
async def player_troops(interaction: discord.Interaction, player_tag: str, village: str ="home"): 
    player_tag = player_tag.replace('#', '%23') 
    url = f'https://api.clashofclans.com/v1/players/{player_tag}' 
    headers = { 'Authorization': f'Bearer {api_key}', 
    'Accept': 'application/json' 
    }

    response = requests.get(url, headers=headers) 
    if response.status_code == 200: 
        player_data = response.json() 
        name = f"Name: {player_data['name']}\n"

        exclude_words = ['super', 'sneaky', 'ice golem', 'inferno', 'rocket balloon', 'ice hound']

        def is_valid_troop(troop): 
            return all(word not in troop['name'].lower() for word in exclude_words)
            
        if village.lower() == 'builder': 
             filtered_troops = [troop for troop in player_data['troops'] if troop['village'] == 'builderBase' and is_valid_troop(troop)]
        elif village.lower() == 'home': 
            filtered_troops = [troop for troop in player_data['troops'] if troop['village'] == 'home' and is_valid_troop(troop)]
        else: 
            filtered_troops = [troop for troop in player_data['troops'] if is_valid_troop(troop)]

      #  filtered_troops = [troop for troop in player_data['troops'] if 'super' not in troop['name'].lower()]

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
        await interaction.response.send_message(f" {name}{troop_information}") 
    else: 
        await interaction.response.send_message(f'Error: {response.status_code}, {response.text}') 

@bot.tree.command(name ="playerheroes", description = "Get a player's heroes/equipments")
@app_commands.describe(player_tag = "The User's tag")
async def player_heroes(interaction: discord.Interaction, player_tag: str):
    playertag = player_tag.replace('#','%23')
    url = f'https://api.clashofclans.com/v1/players/{playertag}'
    headers ={ 'Authorization': f'Bearer {api_key}',
    'Accept': 'application/json'
    }
    response = requests.get(url, headers =headers)
    if response.status_code == 200:
        player_data = response.json()
        name = player_data.get('name')
      

        #Creates a list that iterates over each hero in player_data heroes
        filtered_heroes = [hero for hero in player_data['heroes'] if hero['village'] != 'builderBase'] 
        #Makes a list and iterates through each hero only if they have an associated equipment to them in the heroequipment then goes through until the last equip
      #  filtered_equipment = player_data['heroEquipment']
        filtered_equipment = [equipment for hero in player_data['heroes'] if 'equipment' in hero for equipment in hero['equipment']]

        #Iterates through each hero in filteredheroes and adds formatted string of heroname and level
        hero_details = '\n'.join([
            f"{hero['name']}: Level {hero['level']}/{hero['maxLevel']} {'(MAXED)' if hero['level'] == hero['maxLevel'] else ''}" 
            for hero in filtered_heroes
        ]) 
        #Iterates through each equip in filteredequipment and adds formatted string of equipname and level
        equipment_details = '\n'.join([
            f"{equip['name']}: Level {equip['level']}/{equip['maxLevel']} {'(MAXED)' if equip['level'] == equip['maxLevel'] else ''}" 
            for equip in filtered_equipment
            ])


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
        await interaction.response.send_message(f'{hero_information}')
    else:
        await interaction.response.send_message(f'Error: {response.status_code}, {response.text}')


@bot.tree.command(name = "playerequipments", description = "Get info on all of a player's equipments")
@app_commands.describe(player_tag = "The user's tag")
async def player_equips(interaction: discord.Interaction, player_tag: str):
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
@app_commands.describe(player_tag = "The user's tag")
async def player_spells(interaction: discord.Interaction, player_tag: str):
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

#Lists all clan members in clan 
@bot.tree.command(name="clanmembers", description="Get all member info of the clan sorted by trophies by default") 
@app_commands.describe(ranking= "List by trophies(default), TH, role")
async def clan_members(interaction: discord.Interaction, ranking: str = "TROPHIES"): 
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

        # Sorting members based on the specified ranking criteria
        if ranking.upper() == "TROPHIES":
            sorted_members = sorted(clan_data['items'], key=lambda member: member['trophies'], reverse=True)
        elif ranking.upper() == "TH":
            sorted_members = sorted(clan_data['items'], key=lambda member: member['townHallLevel'], reverse=True)
        elif ranking.upper() == "ROLE":
            role_order = {"leader": 1, "coLeader": 2, "admin": 3, "member": 4}
            sorted_members = sorted(clan_data['items'], key=lambda member: role_order.get(member['role'], 5))
        else:
            await interaction.followup.send("Invalid ranking criteria. Please use: trophies, TH, or role.")
            return

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
            member_info = (
                f"{member['clanRank']}. {member['name']}, Role: {role}, (TH: {member['townHallLevel']})\n"
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
        if 'items'in clan_data:
            clans = clan_data['items']
            clan_info_list = []

            for clan in clans: 
                clan_info = (
                   f"```yaml\n"
                   f"Clan Name: {clan['name']}\n" 
                   f"Clan Level: {clan['clanLevel']}\n" 
                   f"Members: {clan['members']}\n" 
                   f"Type: {clan['type']}\n" 
                   f"War Frequency: {clan['warFrequency']}\n" 
                   f"War Wins: {clan['warWins']}\n" 
                   f"War Log Public? {clan['isWarLogPublic']}\n"
                   f"Location: {clan['location']['name'] if 'location' in clan else 'N/A'}\n" 
                   f"```"
                )
                clan_info_list.append(clan_info)
                clan_info_formatted = "\n".join(clan_info_list)
               
        else:
            clan_info_formatted = "No clans found matching this criteria"

    else:
        clan_info_formatted= "Failed to retrieve clans. Please try again Later."

    await interaction.followup.send(clan_info_formatted)

@bot.tree.command(name="lookupmember", description="Get Clan info for a specific user")
async def user_info(interaction: discord.Interaction, username: str):
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

        for member in clan_data['memberList']:
            if member['name'].lower() == username.lower():
                role = member['role']
                embed = discord.Embed(
                    title=f"{member['name']}",
                    color=discord.Color.green(),
                    description= member['tag']
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
                embed.add_field(name="Trophies", value=f"{member['trophies']} | {member['league']['name']}", inline=False)
                embed.add_field(name="Builder Base Trophies", value=f"{member['builderBaseTrophies']} | {member['builderBaseLeague']['name']}", inline=False)
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
        
        embed = Embed(
            title="Clan Information",
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
        embed.add_field(name="Required BuilderBase Trophies", value=f":trophy: {clan_data['requiredBuilderBaseTrophies']}", inline=True)

        embed.add_field(name="Win/loss ratio", value=f"{clan_data['warWins']} :white_check_mark: / {clan_data['warLosses']} :x:", inline=False)
        embed.add_field(name="Location", value=f":globe_with_meridians: {clan_data['location']['name']}", inline=False)

        await interaction.followup.send(embed=embed)
    elif response.status_code == 404:
        await interaction.followup.send("No information found for the specified clan.")
    else:
        await interaction.followup.send(f"Error retrieving clan info: {response.status_code}, {response.text}")



@bot.tree.command(name="capitalraid", description="Retrieve information about info on current raid for clan")
async def capitalRaid(interaction: discord.Interaction):
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

                reward = reward / total_attacks
                print(reward)
                reward = reward * 6.0
                print(reward)
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
                    description=result,
                color=embed_color  # Apply dynamic color
            )
            
        

            if attacks_per_member == 2:  # Regular War
                embed.add_field(name="Clan Tag", value=our_tag, inline=True)
                embed.add_field(name="Clan Stars", value=f":star: {clan_stars}", inline=True)
                embed.add_field(name="Clan Destruction", value=f"{clan_destruction}%", inline=True)

                embed.add_field(name="Opponent Tag", value=opponent_tag, inline=True)
                embed.add_field(name="Opponent Stars", value=f":star: {opponent_stars}", inline=True)
                embed.add_field(name="Opponent Destruction", value=f"{opp_destruction}%", inline=True)

                embed.add_field(name="Team Size", value=f":bust_in_silhouette: {entry['teamSize']}", inline=True)
                embed.add_field(name="Exp Gained", value=entry['clan']['expEarned'], inline=True)
                embed.add_field(name="Clan Level", value=entry['clan'].get('clanLevel', 'N/A'), inline=True)

            elif attacks_per_member == 1:  # CWL Log
                attacks_per_member*=7
                embed.add_field(name="Clan Stars", value=f":star: {entry['clan']['stars']}", inline=True)
                embed.add_field(name="Clan Destruction", value=f"{clan_destruction}%", inline=True)
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
                description=f"State: :crossed_swords: {state.capitalize()}",
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
            embed.add_field(name="Clan Destruction", value=f"{destruction_percentage}%", inline=True)

            if clan_stars < opp_stars:
                embed.add_field(name="Opponent Tag", value=f":first_place: {war_data['opponent']['tag']}", inline=True)
            else:
                embed.add_field(name="Opponent Tag", value=f":second_place: {war_data['opponent']['tag']}", inline=True)

            embed.add_field(name="Opponent Stars", value=f":star: {opp_stars} (Attacks: {war_data['opponent']['attacks']}/{num_of_attacks})", inline=True)
            embed.add_field(name="Opponent Destruction", value=f"{opp_destruction_percentage}%", inline=True)

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
            attackers_info += (f"{i+1}.{member['name']}: Stars: {member['stars']}, "
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


@bot.tree.command(name="cwlcurrent", description="Receive information about the current war")
async def warInfo(interaction: discord.Interaction):
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
                description=f"State: {war_data['state'].capitalize()}",
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
                embed.add_field(name="Clan Destruction", value=f"{destruction_percentage}%", inline=True)

            embed.add_field(name="Opponent Tag", value=war_data['opponent']['tag'], inline=True)
            embed.add_field(name="Opponent Stars", value=f":star: {opp_stars} (Attacks: {war_data['opponent']['attacks']}/{num_of_attacks})", inline=True)
            embed.add_field(name="Opponent Destruction", value=f"{opp_destruction_percentage}%", inline=True)

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


@bot.tree.command(name = "cwlclansearch", description = "Search up other clans in CWL")
@app_commands.describe(clanname = "The clan's name")
async def CWL_clan_search(interaction: discord.Interaction, clanname: str):
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




bot.run(TOKEN)

    