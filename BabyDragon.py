from tokenize import Double
import discord
import os
import requests
import praw
from datetime import timedelta
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta 
import random

TOKEN = os.getenv('DISCORD_TOKEN2')
api_key = os.getenv('COC_api_key')
clan_tag = '#2QQ2VCU82'.replace('#', '%23')


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix = "!", intents= intents)


def format_datetime(dt_str):
    if not dt_str:
        return "N/A"
    try: 
        dt = datetime.strptime(dt_str,'%Y%m%dT%H%M%S.%fZ')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
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
@app_commands.checks.has_any_role("Admin", "Co-Leaders", "Elders")
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
          

@bot.tree.command(name ="goldpass", description= "Information about start/end of current gold pass")
async def goldpass(interaction: discord.Interaction):
    await interaction.response.defer()
    url = f'https://api.clashofclans.com/v1/goldpass/seasons/current'
    headers = {
        'Authorization': f'Bearer {api_key}',
    'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)
    if response.status_code ==200:
        gold_pass_data = response.json()
        
        start = gold_pass_data.get('startTime')
        end = gold_pass_data.get('endTime')

        start_date = format_datetime(start)
        end_date = format_datetime(end)
        pass_info = (
            f"** Gold Pass:**\n"
            f"```yaml\n"
           # f"Current Gold Pass Season: {gold_pass_data['name']}\n"
            f"Start Date:{start_date}\n"
            f"End Date:{end_date}\n"
            f"```"

        )
        await interaction.followup.send(pass_info)
    else: 
        await interaction.followup.send(f"Error retrieving gold pass information: {response.status_code}, {response.text}")
    

@bot.tree.command(name = "playerinfo", description = "Get player's general information")
async def player_info(interaction: discord.Interaction, player_tag: str):
   # player_tag = '#LOLLG98LJ'.replace('#', '%23')
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

        player_information = (
            f"**Player Information**\n" 
            f"```yaml\n"
            f"Name: {player_data['name']}\n" 
            f"Tag: {player_data['tag']}\n"
            f"THLVL: {player_data['townHallLevel']}\n" 
            f"Trophies: {player_data['trophies']}\n" 
            f"Best Trophies: {player_data['bestTrophies']}\n"
            f"{filtered_labels}"
            f"```\n"

    )
        await interaction.response.send_message(f"{player_information}")
    else: 
        await interaction.response.send_message(f"Error getting player information")




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

        exclude_words = ['super', 'sneaky', 'ice golem', 'inferno']

        def is_valid_troop(troop): 
            return all(word not in troop['name'].lower() for word in exclude_words)
            
        if village.lower() == 'builder': 
             filtered_troops = [troop for troop in player_data['troops'] if troop['village'] == 'builderBase' and is_valid_troop(troop)]
        elif village.lower() == 'home': 
            filtered_troops = [troop for troop in player_data['troops'] if troop['village'] == 'home' and is_valid_troop(troop)]
        else: 
            filtered_troops = [troop for troop in player_data['troops'] if is_valid_troop(troop)]

      #  filtered_troops = [troop for troop in player_data['troops'] if 'super' not in troop['name'].lower()]

        troops = '\n'.join([f"{troop['name']}: Level {troop['level']} {'(MAXED)' if troop['level'] == troop['maxLevel'] else ''}"
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
        filtered_equipment = [equipment for hero in player_data['heroes'] if 'equipment' in hero for equipment in hero['equipment']]

        #Iterates through each hero in filteredheroes and adds formatted string of heroname and level
        hero_details = '\n'.join([f"{hero['name']}: Level {hero['level']} {'(MAXED)' if hero['level'] == hero['maxLevel'] else ''}" 
        for hero in filtered_heroes]) 
        #Iterates through each equip in filteredequipment and adds formatted string of equipname and level
        equipment_details = '\n'.join([f"{equip['name']}: Level {equip['level']} {'(MAXED)' if equip['level'] == equip['maxLevel'] else ''}" 
        for equip in filtered_equipment])


        hero_informaton = (
            f"```yaml\n"
            f"Name: {name} \n"
            f"Tag: {player_data['tag']}\n"
            f"** Hero Levels **\n"
            f"{hero_details}\n"
            f"** Equipment Levels **\n"
            f"{equipment_details}\n"
            f"```\n"
        )
        await interaction.response.send_message(f'{hero_informaton}')
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
        spell_details = '\n'.join([f"{spell['name']}: Level {spell['level']} {'(MAXED)' if spell['level'] == spell['maxLevel'] else ''}"
         for spell in filtered_spells]) 

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
    await interaction.response.defer() # Defer the interaction to allow time for processing 
    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}' 
    headers = { 'Authorization': f'Bearer {api_key}', 
    'Accept': 'application/json' 
    } 
    response = requests.get(url, headers=headers) 
    if response.status_code == 200: 
        clan_data = response.json() 
        user_found = False

        for member in clan_data['memberList']: 
            if member['name'].lower() == username.lower(): 
                member_info = ( f"**Member Information:**\n" 
                f"```yaml\n"
                f"Player Tag: {member['tag']}\n" 
                f"Name: {member['name']}\n" 
                f"Role: {member['role']}\n" 
                f"Experience Level: {member['expLevel']}\n" 
                f"Trophies: {member['trophies']}\n"
                f"Donations: {member['donations']}\n" 
                f"Donations Received: {member['donationsReceived']}" 
                f"```\n"
                ) 
                chunks = [member_info[i:i + 2000] for i in range(0, len(member_info), 2000)] 
                for chunk in chunks: 
                    await interaction.followup.send(chunk) 

                user_found = True 
                break
        if not user_found: 
            await interaction.followup.send(f'User "{username}" not found in the clan.') 
    else: 
        await interaction.followup.send(f'Error: {response.status_code}, {response.text}')

               
@bot.tree.command(name="claninfo", description="Retrieve information about the clan")
async def clanInfo(interaction: discord.Interaction):
    await interaction.response.defer()  # Defer the interaction to allow time for processing
    if not api_key:
        raise ValueError("API KEY NOT FOUND")
    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)
  #  print(f"Response status: {response.status_code}, Response text: {response.text}")  # Debugging print statement
    if response.status_code == 200:
        clan_data = response.json()
        
        clan_info = (
            f"**Clan Information**\n"
            f"```yaml\n"
            f"Name: {clan_data['name']}\n"
            f"Tag: {clan_data['tag']}\n"
            f"Clan Level: {clan_data['clanLevel']}\n"
            f"Clan Points: {clan_data['clanPoints']}\n"
            f"Members: {clan_data['members']}\n"
            f"Description: {clan_data['description']}\n"
            f"Required Trophies: {clan_data['requiredTrophies']}\n"
            f"Location: {clan_data['location']['name']}\n"
            f"```\n"
        )

        await interaction.followup.send(clan_info)
    elif response.status_code == 404:
        await interaction.followup.send("No information found for the specified clan.")
    else:
        await interaction.followup.send(f"Error retrieving clan info: {response.status_code}, {response.text}")



@bot.tree.command(name="capitalraid", description="Retrieve information about info on current raid for the clan")
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
        for i, entry in enumerate(seasons[:1]):  # Limit to the first 5 seasons for brevity
            state = entry.get('state','N/A' )
            start_time = format_datetime(entry.get('startTime', 'N/A'))
            end_time = format_datetime(entry.get('endTime', 'N/A'))
            capitalTotalLoot = entry.get('capitalTotalLoot')
         #   attack_log = entry.get('attacks', [])

            members = entry.get('members', [])
            attacks = 0
          #  print(f"Members: {members}")
            member_loot_stats = {}
            member_attacks = {}
            for member in members:
               # attacker = attack.get('members', {})
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

            
            raid_info = (
               # f"**Season #{i + 1}**\n"
                f"```yaml\n"
                f"Status: {state}\n"
                f"Start Time: {start_time}\n"
                f"End Time: {end_time}\n"
                f"Total Loot Obtained: {capitalTotalLoot}\n"
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
async def previous_raids(interaction: discord.Interaction):
    await interaction.response.defer()  # Defer the interaction to allow time for processing
    if not api_key:
        raise ValueError("API KEY NOT FOUND")
    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}/capitalraidseasons'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)
 #   print(f"Response status: {response.status_code}, Response text: {response.text}")  # Debugging print statement
    if response.status_code == 200:
        raid_data = response.json()
        seasons = raid_data.get('items', [])
        
        if not seasons:
            await interaction.followup.send("No capital raid seasons found for the specified clan.")
            return

        raid_info_list = []
        for i, entry in enumerate(seasons[:5]):  # Limit to the first 5 seasons for brevity
            state = entry.get('state','N/A' )
            start_time = format_datetime(entry.get('startTime', 'N/A'))
            end_time = format_datetime(entry.get('endTime', 'N/A'))
            capitalTotalLoot = entry.get('capitalTotalLoot')
            raid_info = (
                f"**Season #{i + 1}**\n"
                f"```yaml\n"
                f"Status: {state}\n"
                f"Start Time: {start_time}\n"
                f"End Time: {end_time}\n"
                f"Total Loot Obtained: {capitalTotalLoot}"
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
    

@bot.tree.command(name="warlog", description="Retrieve the war log for the specified clan")
@app_commands.describe(limit = "The number of wars to retrieve (default 1, max 5)" )
async def warLog(interaction: discord.Interaction, limit: int=1):
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
        
        end_time = war_log.get('endTime')
        end_date = format_datetime(end_time)
     #   end_time = format_datetime(war_log.get('endTime', ''))
        if not war_entries:
            await interaction.followup.send("No war log entries found for the specified clan.")
            return

        limit = max(1,min(limit, 5))
        war_entries = war_entries[:limit]

        war_info_list = [
            (
                f'```yaml\n'
                f"**War#{i + 1}**\n"
                f"Result: {entry['result']}\n"
                f"Team Size: {entry['teamSize']}\n"
                f"Opponent: {entry['opponent']['name']} (Tag: {entry['opponent']['tag']})\n"
                f"Clan Stars: {entry['clan']['stars']}, Clan Destruction: {entry['clan']['destructionPercentage']}%\n"
                f"Opponent Stars: {entry['opponent']['stars']}, Opponent Destruction: {entry['opponent']['destructionPercentage']}%\n"
                f"Exp Gained: {entry['clan']['expEarned']}, Clan Level: {entry['clan'].get('clanLevel', 'N/A')}\n"
                f"End Date: {format_datetime(entry.get('endTime', 'N/A'))}\n" # Correctly retrieve and format endTime for each entry
                f"```\n"
            )
            for i, entry in enumerate(war_entries)
        ]

        war_info_message = "\n".join(war_info_list)
        
        await interaction.followup.send(war_info_message)
    elif response.status_code == 404:
        await interaction.followup.send("No war log found for the specified clan.")
    else:
        await interaction.followup.send(f"Error retrieving war log: {response.status_code}, {response.text}")




@bot.tree.command(name = "currentwar", description = "Recieve information about current war")
async def warInfo(interaction:discord.Interaction):
    await interaction.response.defer() # Defer the interaction to allow time for processing 
    
    if not api_key:
        raise ValueError("API KEY NOT FOUND")
    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}/currentwar' 
    headers = { 'Authorization': f'Bearer {api_key}', 
    'Accept': 'application/json' 
    } 
    response = requests.get(url, headers=headers) 
    print(f"Response status: {response.status_code}, Response text: {response.text}") # Debugging print statement
    if response.status_code == 200: 
        war_data = response.json() 

        if war_data['state'] == 'inWar':
            war_info = (
                f'```yaml\n'
                f"**Current War Information**\n"
                f"State: {war_data['state']}\n"
                f"Team Size: {war_data['teamSize']}\n" 
                f"Clan: {war_data['clan']['name']} (Tag: {war_data['clan']['tag']})\n" 
                f"Opponent: {war_data['opponent']['name']} (Tag: {war_data['opponent']['tag']})\n" 
                f"Clan Stars: {war_data['clan']['stars']}\n" 
                f"Opponent Stars: {war_data['opponent']['stars']}\n" 
                f"Clan Destruction Percentage: {war_data['clan']['destructionPercentage']}\n" 
                f"Opponent Destruction Percentage: {war_data['opponent']['destructionPercentage']}\n"
                f"```\n"

        )
        if war_data['state'] == 'notInWar':
            war_info = (
                f"```yaml\n"
                f"**Current War Information**\n"
                f"State: {war_data['state']}\n"
                f"```\n"
            )

        await interaction.followup.send(war_info)
    elif response.status_code == 404: 
        await interaction.followup.send("No current war found for the specified clan.")
    else:
        await interaction.followup.send(f"Error retrieving current war info: {response.status_code}, {response.text}")

@bot.tree.command(name = "cwlcurrent", description = "Recieve information about current war")
async def warInfo(interaction:discord.Interaction):
    await interaction.response.defer() # Defer the interaction to allow time for processing 
    if not api_key:
        raise ValueError("API KEY NOT FOUND")
    url = f'https://api.clashofclans.com/v1/clans/{clan_tag}/currentwar/leaguegroup' 
    headers = { 'Authorization': f'Bearer {api_key}', 
    'Accept': 'application/json' 
    } 
    response = requests.get(url, headers=headers) 
  #  print(f"Response status: {response.status_code}, Response text: {response.text}") # Debugging print statement
    if response.status_code == 200: 
        war_data = response.json() 

        if 'state' in war_data and war_data['state'] == 'inWar': 
            if 'clans' in war_data: 
                clan_info = "\n".join([ f"Clan{i+1}: {clan['name']} (Tag: {clan['tag']})" 
                for i, clan in enumerate(war_data['clans'])
                ])
                war_info = ( 
                f'```yaml\n' 
                f"**Current CWL Information**\n" 
                f"State: {war_data['state']}\n" 
                f"Season: {war_data['season']}\n" 
                f"{clan_info}\n" 
                f"```\n"
            )
             
            else: 
                war_info = ( 
                f'```yaml\n' f"**Current War Information**\n" 
                f"State: {war_data['state']}\n" 
                f"No clans data available.\n" f"```\n" 
                ) 

        elif 'state' in war_data and war_data['state'] == 'notInWar': 
            war_info = ( f'```yaml\n' 
            f"**Current War Information**\n" 
            f"State: {war_data['state']}\n" 
            f"```\n"

            )
            
        await interaction.followup.send(war_info)
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
    else:
        await interaction.followup.send(f"Error retrieving CWL information: {response.status_code}, {response.text}")




bot.run(TOKEN)

    