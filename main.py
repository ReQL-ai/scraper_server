from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from playwright.async_api import async_playwright

app = FastAPI()

class ScrapeRequest(BaseModel):
    url: str

@app.post("/scrape-site")
async def scrape_site(scrape_request: ScrapeRequest):
    url = scrape_request.url
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000)  # 60 sec timeout
            await page.wait_for_load_state('networkidle')

            # Instead of full body, grab probable content
            # Try to get text from <main> tag first
            content = ""
            if await page.locator('main').count() > 0:
                content = await page.locator('main').inner_text()
            elif await page.locator('article').count() > 0:
                content = await page.locator('article').inner_text()
            elif await page.locator('div#content').count() > 0:
                content = await page.locator('div#content').inner_text()
            else:
                # fallback to full body text
                content = await page.evaluate("document.body.innerText")

            await browser.close()

            clean_text = content.strip()
            if not clean_text:
                raise Exception("No readable text found on page")

            return {"scraped_info": clean_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")
