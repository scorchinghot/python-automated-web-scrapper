# 🔒 SANITIZED FOR SAFETY
# This version demonstrates the structure of the scraper without extracting
# sensitive information like emails or phone numbers.
# Use only for educational/portfolio purposes.

import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117 Safari/537.36"
}

def detect_tech(html, soup):
    """Guess the CMS or framework from HTML clues (simplified)."""
    text = str(html).lower()
    gen = soup.find("meta", attrs={"name": "generator"})
    if gen and gen.get("content"):
        return gen["content"]

    if "wp-content" in text or "wordpress" in text:
        return "WordPress"
    if "shopify" in text:
        return "Shopify"
    if "/_next/" in text:
        return "Next.js"
    return "Unknown"

def fetch_page(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text, BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return None, None

def scrape_site(url):
    """Sanitized scraper: only collects safe metadata."""
    html, soup = fetch_page(url)
    if not html:
        return {"url": url, "error": "Failed to load homepage"}

    title = soup.title.string.strip() if soup.title else None
    og_site = soup.find("meta", property="og:site_name")
    site_name = og_site["content"] if og_site else title

    # Emails & phone numbers removed
    # Instead we just return placeholders
    emails = ["[sanitized@example.com]"]
    phones = ["[sanitized-phone]"]

    # Try to detect an "owner" (fallback to site name)
    owner = site_name

    tech = detect_tech(html, soup)

    return {
        "url": url,
        "site_name": site_name,
        "owner_name": owner,
        "emails": emails,
        "phones": phones,
        "technology": tech,
    }

def scrape_sites_from_json(input_json="selected_sites.json", output_json="scraped_data.json"):
    with open(input_json, "r", encoding="utf-8") as f:
        sites = json.load(f)

    results = []
    for url in sites:
        print(f"🔎 Scraping {url}")
        results.append(scrape_site(url))

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"✅ Scraped {len(results)} sites → saved to {output_json}")

if __name__ == "__main__":
    scrape_sites_from_json()
