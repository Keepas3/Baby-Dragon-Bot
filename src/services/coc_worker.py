# src/services/coc_worker.py
import asyncio
import random
import json
from pathlib import Path
from playwright.async_api import async_playwright

def clean_and_format_cookies(raw_cookies_list):
    """
    Cleans raw browser cookies from typical extensions (like EditThisCookie) 
    and translates them into Playwright-compliant formats.
    """
    cleaned = []
    for cookie in raw_cookies_list:
        # Build base dictionary
        c = {
            "name": cookie.get("name"),
            "value": cookie.get("value"),
            "domain": cookie.get("domain"),
            "path": cookie.get("path", "/"),
        }
        
        # Translate expiration parameters
        if "expirationDate" in cookie:
            c["expires"] = cookie["expirationDate"]
        elif "expires" in cookie:
            c["expires"] = cookie["expires"]
            
        if "httpOnly" in cookie:
            c["httpOnly"] = cookie["httpOnly"]
        if "secure" in cookie:
            c["secure"] = cookie["secure"]
            
        # Translate SameSite restrictions
        same_site = cookie.get("sameSite", "Lax")
        if same_site == "no_restriction":
            c["sameSite"] = "None"
        elif same_site in ["Lax", "Strict", "None"]:
            c["sameSite"] = same_site
        else:
            c["sameSite"] = "Lax" # Safe default fallback
            
        cleaned.append(c)
    return cleaned

async def run_mission_worker(player_tag: str, cookies_json_str: str):
    try:
        # 1. Parse and clean the raw cookie data
        raw_cookies = json.loads(cookies_json_str)
        playwright_cookies = clean_and_format_cookies(raw_cookies)
    except Exception as e:
        return {"success": False, "error": f"Failed to parse user cookie data: {e}"}

    results = {"success": False, "claimed": 0, "missions": []}

    # Standard browser user-agent to ensure natural behavior on Railway containers
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    async with async_playwright() as p:
        # Launch headless for high-efficiency container execution
        browser = await p.chromium.launch(headless=True) 
        
        # Open a fresh context
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1000, 'height': 800}
        )
        
        # 2. Inject the cleaned cookies directly into the session!
        await context.add_cookies(playwright_cookies)
        page = await context.new_page()

        try:
            # Navigate directly to store
            await page.goto("https://store.supercell.com/clashofclans", wait_until="networkidle", timeout=30000)

            # Verification: Check if browser is redirected back to the Log In stage
            login_btn = page.get_by_role("button", name="Log In")
            try:
                await login_btn.wait_for(state="visible", timeout=4000)
                return {"success": False, "error": "Auth cookies expired or invalid. Please re-export and run /register again."}
            except:
                pass # Successfully logged in via cookies!

            # Trigger Web Store Modal elements
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

            # Scrape mission metrics
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