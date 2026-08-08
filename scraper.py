from openai import base_url
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

#What each does:
# 1. requests — lets Python visit websites and download their content (like a browser without the visuals)
# 2. BeautifulSoup — parses HTML code so we can extract text and links from web pages
# 3. urljoin — combines a base URL with a relative link (e.g., /en/page + https://site.com = full URL)
# 4. urlparse — breaks a URL into parts so we can check if a link belongs to the same website
# 5. time — lets us pause between requests so we don't overload the server

def get_all_text(base_url, max_pages=50):
    visited = set()
    to_visit = [base_url]
    all_text = ""
    base_domain = urlparse(base_url).netloc  

# 1. def get_all_text(base_url, max_pages=50): — Creates a function named get_all_text that takes a starting URL and a limit of how many pages to scrape (default 50)
# 2. visited = set() — An empty set to track URLs we've already scraped. A set automatically prevents duplicates
# 3. to_visit = [base_url] — A list of URLs waiting to be scraped. We start with just the one you gave us
# 4. all_text = "" — An empty string that will eventually hold all the text from every page combined  
# 5. urlparse(base_url) — Breaks your URL into pieces (scheme, domain, path, etc.)
# 6. .netloc — Extracts just the domain part
# Example: URL: https://bharatpurmun.gov.np/en/node/27  || .netloc → "bharatpurmun.gov.np"

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue

#url = to_visit.pop(0) — Take the first URL from the queue (and remove it from the list)