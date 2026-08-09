import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import io
import PyPDF2
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# What each does:
# 1. requests — lets Python visit websites and download their content (like a browser without the visuals)
# 2. BeautifulSoup — parses HTML code so we can extract text and links from web pages
# 3. urljoin — combines a base URL with a relative link (e.g., /en/page + https://site.com = full URL)
# 4. urlparse — breaks a URL into parts so we can check if a link belongs to the same website
# 5. time — lets us pause between requests so we don't overload the server
# 6. io — Handles files in memory (we don't need to save PDFs to disk)
# 7. PyPDF2 — Extracts text from PDF files

def get_all_text(base_url, max_pages=50):
    # Creates a function named get_all_text that takes a starting URL and a limit of how many pages to scrape (default 50)
    visited = set()
    # An empty set to track URLs we've already scraped. A set automatically prevents duplicates
    to_visit = [base_url]
    # A list of URLs waiting to be scraped. We start with just the one you gave us
    all_text = ""
    # An empty string that will eventually hold all the text from every page combined
    base_domain = urlparse(base_url).netloc
    # urlparse(base_url) — Breaks your URL into pieces (scheme, domain, path, etc.)
    # .netloc — Extracts just the domain part
    # Example: URL: https://bharatpurmun.gov.np/en/node/27  || .netloc → "bharatpurmun.gov.np"

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        # url = to_visit.pop(0) — Take the first URL from the queue (and remove it from the list)
        if url in visited:
            continue

        if url.endswith(('.jpg', '.png', '.gif', '.doc', '.docx', '.xls', '.xlsx')):
            continue
        
        # Check if it's a PDF — handle differently
        is_pdf = url.lower().endswith('.pdf')

        try:
            print(f"Scraping: {url}")
            resp = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }, verify=False)
            # requests.get(url, timeout=30, headers=...) — Downloads the page
            # timeout=30 — Wait max 30 seconds
            # User-Agent — Pretends to be a real browser so websites don't block us
            
            if resp.status_code != 200:
                print(f"  -> Skipped (status {resp.status_code})")
                continue
            # resp.status_code — 200 = success, 404 = not found, etc.
            # If it's not 200, skip this page

            if is_pdf:
                # If it's a PDF:
                # io.BytesIO(resp.content) — Loads the PDF into memory (no file saved to disk)
                pdf_file = io.BytesIO(resp.content)
                reader = PyPDF2.PdfReader(pdf_file)
                # PyPDF2.PdfReader(pdf_file) — Opens the PDF for reading
                content = ""
                for page in reader.pages:
                    # reader.pages — Gets all pages
                    page_text = page.extract_text()
                    # page.extract_text() — Pulls text from each page
                    if page_text:
                        content += page_text + "\n"
                if content:
                    print(f"  -> Extracted {len(content)} chars from PDF")
                    # Prints how much text was found
            else:
                # If it's a normal web page:
                # BeautifulSoup(resp.text, 'html.parser') — Parses the HTML
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Removes junk elements (scripts, styles, navigation menus)
                for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                
                # Tries to find the main content area first
                # main_content is the result of searching for <main>, <article>, or a class="content" div.
                # If we found one, extract text only from that section. This gives us clean, focused content
                main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
                if main_content:
                    content = main_content.get_text(separator='\n', strip=True)
                else:
                    # If we couldn't find a main section, grab text from the entire page.
                    # Less clean, but better than getting nothing
                    content = soup.get_text(separator='\n', strip=True)

            # if content: — Only add if we actually got text from the page
            if content:
                all_text += f"\n--- Page: {url} ---\n"
                # all_text += f"\n--- Page: {url} ---\n" — Adds a label showing which page this text came from
                all_text += content + "\n"
                # all_text += content + "\n" — Appends the actual text
            
            visited.add(url)
            # visited.add(url) — Marks this URL as scraped so we don't revisit it

            # if not is_pdf: — Only search for links in HTML pages (PDFs don't have links we can follow)
            if not is_pdf:
                for link in soup.find_all('a', href=True):
                    # soup.find_all('a', href=True) — Finds every clickable link on the page
                    href = urljoin(base_url, link['href'])
                    # urljoin(base_url, link['href']) — Turns /en/page into https://bharatpurmun.gov.np/en/page
                    parsed = urlparse(href)
                    if parsed.netloc == base_domain and href not in visited and href not in to_visit:
                        # parsed.netloc == base_domain — Checks the link is on the same website
                        # href not in visited and href not in to_visit — Only adds truly new links
                        to_visit.append(href)
                        # to_visit.append(href) — Adds the new link to the queue
            
            time.sleep(0.5)
            # Pause between requests to be polite to the server
            
        except Exception as e:
            print(f"  -> Failed: {e}")

    return all_text


# ============================================================
# THE RUNNER CODE — Modified for slow websites
# ============================================================
# Instead of crawling 30 pages automatically (which times out on slow servers),
# we manually list important URLs and scrape them one by one with longer waits.

if __name__ == "__main__":
    # List of important pages to scrape — add more URLs as needed
    important_urls = [
        "https://bharatpurmun.gov.np/en/node/27",
        "https://bharatpurmun.gov.np/en",
        "https://bharatpurmun.gov.np/en/introduction",
        "https://bharatpurmun.gov.np/en/organization-structure",
        "https://bharatpurmun.gov.np/en/services",
        # Add any other specific pages you want the chatbot to know about
    ]
    
    all_text = ""
    total_scraped = 0
    
    for i, url in enumerate(important_urls, 1):
        print(f"\n[{i}/{len(important_urls)}] Scraping: {url}")
        print("-" * 40)
        
        try:
            # Download the page with a longer timeout
            resp = requests.get(url, timeout=60, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }, verify=False)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Remove junk elements
                for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                
                # Try to find main content
                main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
                if main_content:
                    content = main_content.get_text(separator='\n', strip=True)
                else:
                    content = soup.get_text(separator='\n', strip=True)
                
                if content:
                    all_text += f"\n--- Page: {url} ---\n"
                    all_text += content + "\n"
                    total_scraped += len(content)
                    print(f"  -> Success! ({len(content)} characters)")
                else:
                    print(f"  -> No content found on this page")
            else:
                print(f"  -> Skipped (status {resp.status_code})")
                
        except Exception as e:
            print(f"  -> Failed: {e}")
        
        # Longer delay between requests for slow servers
        time.sleep(3)
    
    # Save everything to a file
    with open("website_content.txt", "w", encoding="utf-8") as f:
        # Creates a text file to save everything
        f.write(text)
        # f.write(text) — Writes all scraped text to the file
    
    print(f"\n{'='*50}")
    print(f"Done! Scraped {total_scraped} characters from {len(important_urls)} pages.")
    print(f"Content saved to website_content.txt")