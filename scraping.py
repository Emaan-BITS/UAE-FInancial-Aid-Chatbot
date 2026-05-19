import os
import time
import random
import zipfile
import io
import hashlib
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Import Playwright for headless browsing
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Move the 10 successfully extracted banks here to skip them
COMPLETED_BANKS = [
    "HSBC Bank Middle East Limited",
    "Standard Chartered Bank",
    "Emirates NBD Bank P.J.S.C",
    "CitiBank N.A.",
    "First Abu Dhabi Bank P.J.S.C",
    "National Bank of R.A.K P.J.S.C (RAKBANK)",
    "Al Hilal Bank P.J.S.C",
    "Bank of Sharjah P.J.S.C",
    "WIO Bank P.J.S.C",
    "Al Maryah Community Bank L.L.C."
]

bank_targets = [
    # --- MAJOR UAE BANKS ---
    {
        "institution_name": "HSBC Bank Middle East Limited",
        "url": "https://www.hsbc.ae/help/download-centre/",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Standard Chartered Bank",
        "url": "https://www.sc.com/ae/help-centre/downloads/",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Emirates NBD Bank P.J.S.C",
        "url": "https://www.emiratesnbd.com/en/help-and-support/forms",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "CitiBank N.A.",
        "url": "https://www.citibank.ae/english/forms/forms.htm",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Mashreq Bank P.S.C.",
        "url": "https://www.mashreq.com/en/uae/personal/help-and-support/forms/",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "First Abu Dhabi Bank P.J.S.C",
        "url": "https://www.bankfab.com/en-ae/personal/forms-and-downloads",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Abu Dhabi Commercial Bank P.J.S.C",
        "url": "https://www.adcb.com/en/personal/support/downloads/",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Dubai Islamic Bank P.J.S.C",
        "url": "https://www.dib.ae/help-support/forms",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Abu Dhabi Islamic Bank P.J.S.C",
        "url": "https://www.adib.ae/en/Pages/Downloads.aspx",
        "pdf_selector": "a[href*='.pdf']"
    },

    # --- REMAINING CBUAE REGISTERED BANKS ---
    {
        "institution_name": "Commercial Bank of Dubai P.J.S.C",
        "url": "https://www.cbd.ae/personal/help-support/downloads",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Emirates Islamic Bank P.J.S.C.",
        "url": "https://www.emiratesislamic.ae/en/help-and-support/forms",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "National Bank of R.A.K P.J.S.C (RAKBANK)",
        "url": "https://rakbank.ae/en/personal/support/forms",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Sharjah Islamic Bank P.J.S.C.",
        "url": "https://www.sib.ae/en/help-and-support/downloads",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Ajman Bank P.J.S.C",
        "url": "https://www.ajmanbank.ae/en/downloads.html",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Al Hilal Bank P.J.S.C",
        "url": "https://www.alhilalbank.ae/en/personal/support/downloads/",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Commercial Bank International P.J.S.C",
        "url": "https://www.cbiuae.com/en/personal/support/downloads",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "National Bank of Fujairah PSC",
        "url": "https://www.nbf.ae/en/personal/support/downloads",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "United Arab Bank P.J.S.C",
        "url": "https://www.uab.ae/en/personal/support/downloads",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Bank of Sharjah P.J.S.C",
        "url": "https://www.bankofsharjah.com/en/downloads",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "InvestBank P.J.S.C",
        "url": "https://www.investbank.ae/downloads",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "National Bank of U.A.Q PSC",
        "url": "https://www.nbq.ae/en/downloads",
        "pdf_selector": "a[href*='.pdf']"
    },
    
    # --- DIGITAL & COMMUNITY BANKS ---
    {
        "institution_name": "WIO Bank P.J.S.C",
        "url": "https://wio.io/downloads",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Zand Bank P.J.S.C",
        "url": "https://zand.ae/en/downloads",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Al Maryah Community Bank L.L.C.",
        "url": "https://www.mbank.ae/downloads/",
        "pdf_selector": "a[href*='.pdf']"
    },

    # --- TOP NON-BANK INSTITUTIONS ---
    {
        "institution_name": "Al Ansari Exchange L.LC.",
        "url": "https://alansariexchange.com/downloads/",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Al Fardan Exchange L.L.C",
        "url": "https://alfardanexchange.com/downloads",
        "pdf_selector": "a[href*='.pdf']"
    },
    {
        "institution_name": "Amlak Finance PJSC",
        "url": "https://www.amlakfinance.com/en/downloads/",
        "pdf_selector": "a[href*='.pdf']"
    }
]

def human_delay():
    """Adds a randomized delay to mimic human reading/clicking behavior."""
    delay = random.uniform(3.0, 6.0)
    print(f"    [~] Pausing for {delay:.2f}s...")
    time.sleep(delay)

def extract_pdfs(page, context, bank, zip_file, written_files_tracker):
    """Finds and downloads PDFs using the Playwright page session."""
    name = bank["institution_name"]
    target_url = bank["url"]
    
    try:
        page.goto(target_url, wait_until="networkidle", timeout=20000)
    except PlaywrightTimeoutError:
        print(f"    [!] Timeout reached waiting for network to idle. Proceeding with loaded HTML...")
    except Exception as e:
        print(f"    [!] Error navigating to page: {e}")
        return

    human_delay()
    
    try:
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        pdf_links = soup.select(bank["pdf_selector"])
        unique_pdf_hrefs = {str(link.get('href')) for link in pdf_links if link.get('href')}

        if not unique_pdf_hrefs:
            print(f"    [-] No PDFs found on the page.")
            return

        print(f"    [+] Found {len(unique_pdf_hrefs)} unique PDF links.")
        
        for href in unique_pdf_hrefs:
            pdf_url = urljoin(target_url, str(href))
            pdf_filename = pdf_url.split("/")[-1].split("?")[0]
            
            if not pdf_filename.lower().endswith('.pdf'):
                url_hash = hashlib.md5(pdf_url.encode('utf-8')).hexdigest()[:10]
                pdf_filename = f"document_{url_hash}.pdf"
                
            zip_path = f"{name}/documents/{pdf_filename}"
            
            # Prevent writing duplicate filenames into the same zip path
            if zip_path in written_files_tracker:
                continue
            written_files_tracker.add(zip_path)
            
            print(f"    [->] Downloading: {pdf_filename}")
            
            # Send specific headers to bypass 403 Forbidden WAF blocks
            response = context.request.get(
                pdf_url,
                headers={
                    "Referer": target_url,
                    "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
                }
            )
            
            if response.ok:
                zip_file.writestr(zip_path, response.body())
            else:
                print(f"    [!] Failed to download PDF. Status: {response.status}")
                
    except Exception as e:
        print(f"    [!] Error during PDF extraction: {e}")

def run_scraper():
    zip_buffer = io.BytesIO()
    written_files_tracker = set()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True) 
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                accept_downloads=True
            )
            page = context.new_page()

            for bank in bank_targets:
                name = bank["institution_name"]
                
                if name in COMPLETED_BANKS:
                    print(f"\n[=] Skipping {name}: Already downloaded.")
                    continue
                
                if "<domain>" in bank["url"]:
                    print(f"\n[!] Skipping {name}: Target URL needs manual configuration.")
                    continue

                print(f"\n[*] Accessing Document Hub for {name}...")
                extract_pdfs(page, context, bank, zip_file, written_files_tracker)
                    
            browser.close()
                
    with open("cbuae_financial_data_batch2.zip", "wb") as f:
        f.write(zip_buffer.getvalue())
        
    print("\n[***] Data pipeline complete. Saved to 'cbuae_financial_data_batch2.zip'")

if __name__ == "__main__":
    run_scraper()