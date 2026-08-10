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
# 8. urllib3 — Disables SSL warnings for sites with old certificates (common with gov sites)


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
   # Example: URL: https://bharatpurmun.gov.np/en  || .netloc → "bharatpurmun.gov.np"


   while to_visit and len(visited) < max_pages:
       url = to_visit.pop(0)
       # url = to_visit.pop(0) — Take the first URL from the queue (and remove it from the list)
       if url in visited:
           continue


       # Skip images, documents, and other non-text files
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
           # timeout=30 — Wait max 30 seconds for slow government servers
           # User-Agent — Pretends to be a real browser so websites don't block us
           # verify=False — Skips SSL certificate verification for old/insecure government sites
          
           if resp.status_code != 200:
               print(f"  -> Skipped (status {resp.status_code})")
               continue
           # resp.status_code — 200 = success, 404 = not found, etc.
           # If it's not 200, skip this page and move to the next one


           if is_pdf:
               # If it's a PDF:
               # io.BytesIO(resp.content) — Loads the PDF into memory (no file saved to disk)
               pdf_file = io.BytesIO(resp.content)
               reader = PyPDF2.PdfReader(pdf_file)
               # PyPDF2.PdfReader(pdf_file) — Opens the PDF for reading
               content = ""
               for page in reader.pages:
                   # reader.pages — Gets all pages in the PDF
                   page_text = page.extract_text()
                   # page.extract_text() — Pulls text from each page
                   if page_text:
                       content += page_text + "\n"
               if content:
                   print(f"  -> Extracted {len(content)} chars from PDF")
                   # Prints how much text was found in the PDF
           else:
               # If it's a normal web page:
               # BeautifulSoup(resp.text, 'html.parser') — Parses the HTML into a usable format
               soup = BeautifulSoup(resp.text, 'html.parser')
              
               # Removes junk elements (scripts, styles, navigation menus)
               # This gives us cleaner, more relevant text
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
               # all_text += content + "\n" — Appends the actual text to our collection
          
           visited.add(url)
           # visited.add(url) — Marks this URL as scraped so we don't revisit it


           # if not is_pdf: — Only search for links in HTML pages (PDFs don't have clickable links we can follow)
           if not is_pdf:
               for link in soup.find_all('a', href=True):
                   # soup.find_all('a', href=True) — Finds every clickable link on the page
                   href = urljoin(base_url, link['href'])
                   # urljoin(base_url, link['href']) — Turns /en/page into https://bharatpurmun.gov.np/en/page
                   parsed = urlparse(href)
                   if parsed.netloc == base_domain and href not in visited and href not in to_visit:
                       # parsed.netloc == base_domain — Checks the link is on the same website
                       # href not in visited and href not in to_visit — Only adds truly new links we haven't seen
                       to_visit.append(href)
                       # to_visit.append(href) — Adds the new link to the queue for later scraping
          
           time.sleep(0.5)
           # Pause for 0.5 seconds between requests to be polite to the server
          
       except Exception as e:
           print(f"  -> Failed: {e}")
           # If anything goes wrong (timeout, connection error, etc.), print the error and move on
           # The scraper won't crash — it will just skip this page and try the next one


   return all_text
   # Returns all the collected text back to the runner code below




# ============================================================
# THE RUNNER CODE — This is what actually starts the scraper
# ============================================================


if __name__ == "__main__":
   # __name__ == "__main__" means this code only runs when you execute the file directly
   # (not when imported by another Python file)
  
   # Start from the homepage — it's the fastest-loading page on the site
   base_url = "https://bharatpurmun.gov.np/en"
   print(f"Starting scrape from {base_url}")
   print("=" * 50)
  
   # Call our function to scrape up to 10 pages, starting from the homepage
   # It will automatically find and follow links to other pages on the same site
   all_text = get_all_text(base_url, max_pages=10)
  
   # Open a text file to save everything we scraped
   with open("website_content.txt", "w", encoding="utf-8") as f:
       # "w" = write mode (overwrites any existing file)
       # encoding="utf-8" = supports Nepali and other Unicode characters
       f.write(all_text)
       # Writes all the scraped text to the file
  
   # Print a success message with stats
   print(f"\n{'='*50}")
   print(f"Done! Scraped {len(all_text)} characters.")
   print(f"Content saved to website_content.txt")


   """
============================================================
BHARATPUR MUNICIPALITY WEBSITE SCRAPER
============================================================


This script scrapes content from the Bharatpur Metropolitan City website
(https://bharatpurmun.gov.np) to build a knowledge base for a chatbot.


WHAT IT DOES:
- Starts from the homepage and crawls through internal links
- Extracts clean text from both HTML pages and PDF documents
- Skips images, office documents, and non-text files
- Saves all scraped content to "website_content.txt"


KEY FEATURES:
- PDF Support: Extracts text from PDF files using PyPDF2
- Smart Filtering: Removes navigation, scripts, and styling from HTML
- Error Handling: Continues scraping even if individual pages fail
- Rate Limiting: Waits 0.5 seconds between requests (polite to server)
- Domain-Locked: Only follows links within bharatpurmun.gov.np


HOW TO USE:
   python scraper.py


CONFIGURATION:
- Change max_pages in the runner code to scrape more/fewer pages
- Change base_url to scrape a different website
- Increase timeout for very slow websites


OUTPUT:
   website_content.txt — All scraped text, ready for the chatbot
============================================================
"""

