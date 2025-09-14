# 🔒 SANITIZED FOR SAFETY
# The original used Google search automation with Selenium.
# This version is sanitized: it only loads example links from a local JSON
# or returns a hardcoded list for demonstration.
# Use only for educational/portfolio purposes.

import json

def google_search_scrape(query, num_pages=1, delay=2):
    """Sanitized demo: returns example links instead of scraping Google."""
    print(f"[Demo] Pretending to search for: '{query}' ({num_pages} pages)")
    demo_links = [
        "https://www.examplebusiness.com",
        "https://www.sampleshop.org",
        "https://www.demorestaurant.net"
    ]
    return demo_links

def google_search_scrape_local(query, num_pages=1):
    return google_search_scrape(query, num_pages=num_pages)

if __name__ == "__main__":
    search_query = "demo business search"
    pages_to_scrape = 1

    print(f"🔍 Searching for: {search_query}")
    results = google_search_scrape(search_query, num_pages=pages_to_scrape)

    filename = "scraped_links.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    print(f"🔎 Scraped {len(results)} demo links.")
    print(f"📂 Saved to {filename}")
