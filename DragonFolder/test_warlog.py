import asyncio
import os
from config import coc_client, initialize_coc
from utils import get_war_log_data

async def test_function():
    print("--- Starting War Log Test ---")
    
    # 1. Log in to the Clash of Clans API
    await initialize_coc()
    
    # 2. Define the tag you want to test
    # Use a clan known to have a public war log, e.g., #2Y28CGP8
    test_tag = "#2JL280GJJ" 
    
    try:
        # 3. Call the helper function
        print(f"Fetching log for {test_tag}...")
        war_entries = await get_war_log_data(test_tag)
        
        # 4. Verify the results
        if not war_entries:
            print("Result: No war log found (Log might be private).")
        else:
            print(f"Success! Found {len(war_entries)} log entries.")
            
            # Replace your previous print block with this:
        first = war_entries[0]
        clan_name = first.clan.name
        # Safe check for opponent
        opp_name = first.opponent.name if first.opponent else "CWL Opponent"
        
        print(f"Latest War: {clan_name} vs {opp_name}")
        print(f"Result: {first.result} | Stars: {first.clan.stars}")

    except Exception as e:
        print(f"Test Failed with error: {e}")
    
    # 5. Close the client connection
    await coc_client.close()
    print("--- Test Complete ---")

if __name__ == "__main__":
    asyncio.run(test_function())