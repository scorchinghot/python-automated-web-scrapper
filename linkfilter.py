# DOESN'T NEED TO BE TOUCHED KEEP EXACTLY AS IS

# ---- DO NOT TOUCH ----
import json
import re
import time
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import tldextract

TIMEOUT = 6
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/117.0.0.0 Safari/537.36"}
# Weights for scoring — tuneable
WEIGHTS = {
    "has_phone": 45,
    "has_email": 18,
    "has_contact_link": 20,
    "schema_localbusiness": 55,
    "biz_kw_in_title": 22,
    "biz_kw_in_meta": 12,
    "domain_keyword": 18,
    "short_brand_domain": 10,
    "junk_kw_in_title": -36,
    "long_title_penalty": -10,
    "path_is_article": -18,
    "publisher_domain_penalty": -999  # immediate reject for known publishers
}

# Blacklists 
PUBLISHER_DOMAINS = {
    "yelp.com","tripadvisor.com","timeout.com","eater.com","latimes.com",
    "sfchronicle.com","nytimes.com","forbes.com","wikipedia.org","angieslist.com",
    "thumbtack.com","expertise.com","homeadvisor.com","broadly.com"
}
JUNK_PATH_KEYWORDS = {"blog","article","news","review","story","guide","list","best","top","ranking","magazine","press","insight"}
JUNK_TITLE_KEYWORDS = {"top","best","guide","review","list","rank","ranking","how to","how-to","things to do","things to see"}
BUSINESS_KEYWORDS = {"inc","llc","company","co.","roof","roofing","plumb","plumber","plumbing","dentist","dental","restaurant","cafe","bar","salon","spa","contractor","contracting","services","service","shop","store","clinic","bakery","hotel"}
GOOD_TLDS = {".com", ".net", ".org", ".biz", ".co", ".restaurant"}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I)
PHONE_RE = re.compile(r"(\+?\d[\d\-\.\s\(\)]{6,}\d)")

def get_root_domain(url):
    parsed = urlparse(url)
    ext = tldextract.extract(parsed.netloc)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    return parsed.netloc.lower()

def fetch_page(url):
    """Fetch page text (with a short timeout). returns (text, final_url) or (None, None)"""
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
        if r.status_code == 200 and 'text/html' in r.headers.get('Content-Type',''):
            return r.text, r.url
    except Exception:
        return None, None
    return None, None

def extract_title_meta(html):
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string or "").strip() if soup.title else ""
    desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    meta = desc_tag["content"].strip() if desc_tag and desc_tag.has_attr("content") else ""
    return title, meta

def find_contact_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.select("a[href]"):
        href = a["href"].lower()
        text = (a.get_text(" ", strip=True) or "").lower()
        if "contact" in href or "contact" in text or "book" in href or "appointment" in text or "reserve" in href:
            links.append(urljoin(base_url, a["href"]))
    return links

def has_schema_localbusiness(html):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            txt = script.string or ""
            if "LocalBusiness" in txt or "Organization" in txt:
                return True
        except Exception:
            continue
    return False

def count_phone_email(html):
    emails = set(EMAIL_RE.findall(html or ""))
    phones = set(PHONE_RE.findall(html or ""))
    # lightweight cleanup
    phones = {p for p in phones if len(re.sub(r'\D','',p)) >= 7}
    return len(phones), len(emails)

def score_domain(domain, sample_url=None):
    
    if any(pub in domain for pub in PUBLISHER_DOMAINS):
        return {"domain": domain, "score": WEIGHTS["publisher_domain_penalty"], "reason": "publisher-domain", "kept_url": None}

    homepage = f"https://{domain}"
    pages_to_try = [homepage]
    if sample_url:
        pages_to_try.insert(0, sample_url)

    best_score = -9999
    best_features = None
    kept_url = None

    for url in pages_to_try:
        html, final_url = fetch_page(url)
        if html is None:
            continue

        title, meta = extract_title_meta(html)
        title_l = title.lower()
        meta_l = meta.lower()
        combined = f"{title_l} {meta_l}"

        # base score
        score = 0
        features = {}
        if has_schema_localbusiness(html):
            score += WEIGHTS["schema_localbusiness"]
            features["schema"] = True
        contact_links = find_contact_links(html, final_url)
        if contact_links:
            score += WEIGHTS["has_contact_link"]
            features["contact_links"] = contact_links[:3]
        phone_count, email_count = count_phone_email(html)
        if phone_count:
            score += WEIGHTS["has_phone"]
            features["phone_count"] = phone_count
        if email_count:
            score += WEIGHTS["has_email"]
            features["email_count"] = email_count
        if any(kw in combined for kw in BUSINESS_KEYWORDS):
            score += WEIGHTS["biz_kw_in_title"]
            features["biz_kw"] = True
        if any(kw in meta_l for kw in BUSINESS_KEYWORDS):
            score += WEIGHTS["biz_kw_in_meta"]
        if any(kw in domain for kw in ["roof","plumb","plumbing","clinic","salon","dent","restaurant","cafe","hvac","electric"]):
            score += WEIGHTS["domain_keyword"]
            features["domain_kw"] = True
        nd = domain.split(".")[0]
        if len(nd) <= 20 and "." not in nd and len(domain) < 25:
            score += WEIGHTS["short_brand_domain"]
            features["brand_like"] = True
        if any(jk in combined for jk in JUNK_TITLE_KEYWORDS):
            score += WEIGHTS["junk_kw_in_title"]
            features["junk_title"] = True
        parsed = urlparse(final_url)
        path = parsed.path.lower()
        if any(p in path for p in JUNK_PATH_KEYWORDS) and not any(k in domain for k in ["roof","plumb","restaurant","cafe","clinic"]):
            score += WEIGHTS["path_is_article"]
            features["path_is_article"] = True
        title_word_count = len(title.split())
        if title_word_count > 12 and not any(k in domain for k in ["roof","plumb","clinic","restaurant"]):
            score += WEIGHTS["long_title_penalty"]
            features["long_title_words"] = title_word_count

        if score > best_score:
            best_score = score
            best_features = {"title": title, "meta": meta, "url": final_url, **features}
            kept_url = final_url

        time.sleep(0.2)

    if best_features is None:
        return {"domain": domain, "score": -100, "reason": "fetch-failed", "kept_url": None}

    return {"domain": domain, "score": best_score, "features": best_features, "kept_url": kept_url}


def select_business_sites(scraped_links, want=10, max_domains_to_check=60):
    domain_to_sample = {}
    for url in scraped_links:
        d = get_root_domain(url)
        if d not in domain_to_sample:
            domain_to_sample[d] = url

    domains = list(domain_to_sample.items())[:max_domains_to_check]

    results = []
    for domain, sample in domains:
        res = score_domain(domain, sample_url=sample)
        results.append(res)

    results_sorted = sorted(results, key=lambda x: x.get("score", -9999), reverse=True)

    selected = []
    for r in results_sorted:
        if len(selected) >= want:
            break
        if r.get("score", -9999) >= 15:
            selected.append(r)

    idx = 0
    while len(selected) < want and idx < len(results_sorted):
        candidate = results_sorted[idx]
        if candidate not in selected:
            selected.append(candidate)
        idx += 1

    return {"candidates": results_sorted, "selected": selected}

if __name__ == "__main__":
    with open("scraped_links.json", "r", encoding="utf-8") as f:
        scraped = json.load(f)

    out = select_business_sites(scraped, want=10, max_domains_to_check=80)

    with open("domain_scores_debug.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    with open("selected_sites.json", "w", encoding="utf-8") as f:
        json.dump([site["kept_url"] for site in out["selected"] if site.get("kept_url")], f, indent=2)
# ---- DO NOT TOUCH ----