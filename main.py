from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from playwright.async_api import async_playwright
import openai
import os
from openai import AsyncOpenAI

app = FastAPI()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

            # Try extracting the important page text
            content = ""
            if await page.locator('main').count() > 0:
                content = await page.locator('main').inner_text()
            elif await page.locator('article').count() > 0:
                content = await page.locator('article').inner_text()
            elif await page.locator('div#content').count() > 0:
                content = await page.locator('div#content').inner_text()
            else:
                content = await page.evaluate("document.body.innerText")

            # Fetch favicon/logo
            favicon = await page.evaluate('''
                () => {
                    const links = document.querySelectorAll('link[rel~="icon"]');
                    return links.length ? links[0].href : null;
                }
            ''')

            await browser.close()

            clean_text = content.strip()
            if not clean_text:
                raise Exception("No readable text found on page")

            # Generate summary using clean_text (NOW it's available)
            try:
                response = await client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a regulatory compliance expert."},
                        {"role": "user", "content": f"Summarize this business from a regulatory compliance perspective: {clean_text}"}
                    ]
                )
                summary = response.choices[0].message.content
            except Exception as e:
                summary = f"Summary generation failed: {str(e)}"

            return {
                "scraped_info": clean_text,
                "logo_url": favicon,
                "business_summary": summary
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")
