import asyncio
import random
import json
from pathlib import Path
from playwright.async_api import async_playwright

# Dynamically find the absolute path to your 'DRAGON-BOT' root folder
# Moves up 3 levels from: src/services/coc_worker.py -> src/services -> src -> DRAGON-BOT
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT_DIR / "config"

async def run_mission_worker():
    # Load config from the secure config directory
    try:
        config_file = CONFIG_PATH / "browser_config.json"
        with open(config_file, "r") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        return {"success": False, "error": f"Config file missing at {config_file}"}

    results = {"success": False, "claimed": 0, "missions": []}

    async with async_playwright() as p:
        # Launch headless for Discord bot performance
        browser = await p.chromium.launch(headless=True) 
        
        # Reference auth.json inside the config directory
        auth_file = CONFIG_PATH / "auth.json"
        context = await browser.new_context(
            storage_state=str(auth_file),
            user_agent=cfg["user_agent"],
            viewport=cfg["viewport"] 
        )
        page = await context.new_page()

        # Inject session
        init_script = f"const data={cfg['session_storage']}; for(const [k,v] of Object.entries(data)) sessionStorage.setItem(k,v);"
        await page.add_init_script(init_script)

        try:
            # Navigate with a 30s safety timeout
            await page.goto("https://store.supercell.com/clashofclans", wait_until="networkidle", timeout=30000)

            # Verification
            login_btn = page.get_by_role("button", name="Log In")
            try:
                await login_btn.wait_for(state="visible", timeout=4000)
                return {"success": False, "error": "Auth expired. Run auth_manager.py again."}
            except:
                pass # Successfully logged in

            # Trigger Modal
            await page.mouse.wheel(0, 500) 
            await page.wait_for_timeout(1500) 

            bottom_bar = page.get_by_text("BONUSES TO CLAIM", exact=False)
            if not await bottom_bar.is_visible():
                bottom_bar = page.get_by_text("to next Store bonus", exact=False)

            await bottom_bar.click(force=True)
            await page.wait_for_selector("text=BONUS TRACK", timeout=8000)

            # --- TAB 1: BONUSES ---
            claim_btns = page.get_by_role("button", name="CLAIM")
            claimed_count = await claim_btns.count()
            
            if claimed_count > 0:
                for i in range(claimed_count):
                    await claim_btns.nth(0).click()
                    await page.wait_for_timeout(random.randint(1500, 2500))
                results["claimed"] = claimed_count

            # --- TAB 2: MISSIONS ---
            await page.get_by_role("button", name="Missions").click()
            await page.wait_for_timeout(1000)

            # Scrape using your partial class selectors
            mission_cards = page.locator('[class*="bonusMissionItem_item__"]')
            m_count = await mission_cards.count()

            for i in range(m_count):
                card = mission_cards.nth(i)
                try:
                    title = await card.locator('[class*="bonusMissionItem_title"]').inner_text()
                    progress = await card.locator('[class*="bonusMissionItem_progressText"], [class*="bonusMissionItem_compltetedText"]').inner_text()
                    points = await card.locator('[class*="PointsTag_PointsLabel"]').inner_text()

                    results["missions"].append({
                        "title": title.strip(),
                        "progress": progress.strip(),
                        "reward": points.strip()
                    })
                except:
                    continue

            results["success"] = True

        except Exception as e:
            results["error"] = str(e)
        finally:
            await browser.close()
            
    return results

if __name__ == "__main__":
    # Test run
    data = asyncio.run(run_mission_worker())
    print(json.dumps(data, indent=2))