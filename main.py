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
            await page.wait_for_load_state('domcontentloaded')

            # Get the full visible text
            page_text = await page.evaluate("document.body.innerText")

            await browser.close()
            return {"scraped_info": page_text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")
