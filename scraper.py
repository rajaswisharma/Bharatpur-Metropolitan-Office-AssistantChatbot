from openai import base_url
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import io
import PyPDF2

#What each does:
# 1. requests — lets Python visit websites and download their content (like a browser without the visuals)
# 2. BeautifulSoup — parses HTML code so we can extract text and links from web pages
# 3. urljoin — combines a base URL with a relative link (e.g., /en/page + https://site.com = full URL)
# 4. urlparse — breaks a URL into parts so we can check if a link belongs to the same website
# 5. time — lets us pause between requests so we don't overload the server
# 6. io — Handles files in memory (we don't need to save PDFs to disk)
# 7. PyPDF2 — Extracts text from PDF files

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
        if url.endswith(('.jpg', '.png', '.gif', '.doc', '.docx', '.xls', '.xlsx')):
            continue
        
        # Check if it's a PDF — handle differently
        is_pdf = url.lower().endswith('.pdf')

        if is_pdf:
                # Extract text from PDF
                pdf_file = io.BytesIO(resp.content)
                reader = PyPDF2.PdfReader(pdf_file)
                content = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        content += page_text + "\n"
                if content:
                    print(f"  -> Extracted {len(content)} chars from PDF")
        else:
                # Extract text from HTML page
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                
                main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
                if main_content:
                    content = main_content.get_text(separator='\n', strip=True)
                else:
                    content = soup.get_text(separator='\n', strip=True)

"""

A. If it's a PDF:

io.BytesIO(resp.content) — Loads the PDF into memory (no file saved to disk)

PyPDF2.PdfReader(pdf_file) — Opens the PDF for reading

reader.pages — Gets all pages

page.extract_text() — Pulls text from each page

Prints how much text was found

B. If it's a normal web page:

BeautifulSoup(resp.text, 'html.parser') — Parses the HTML

Removes junk elements (scripts, styles, navigation menus)

Tries to find the main content area first

Falls back to extracting all text if no main section found
"""

# main_content is the result of searching for <main>, <article>, or a class="content" div. If we found one, extract text only from that section. 
# This gives us clean, focused content

# If we couldn't find a main section, grab text from the entire page. Less clean, but better than getting nothing
