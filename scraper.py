import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
import re
from abc import ABC, abstractmethod
import time
import sys

# Configure logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Log to console
    ]
)

# Load environment variables from .env file
load_dotenv()

class JobBoardScraper(ABC):
    """
    Abstract base class for job board scrapers.
    This allows for easy extension to other job boards in the future.
    """
    
    @abstractmethod
    def extract_job_text(self, soup: BeautifulSoup) -> str:
        """
        Abstract method that must be implemented by child classes.
        Extracts job description text from a BeautifulSoup object.
        """
        pass
        
    def clean_text(self, text: str) -> str:
        """
        Cleans and formats the extracted text:
        - Removes excessive newlines
        - Removes multiple spaces
        - Removes empty lines
        Returns cleaned text string.
        """
        if not text:
            return ""
            
        text = re.sub(r'\n{3,}', '\n\n', text)  # Replace 3+ newlines with 2
        text = re.sub(r' +', ' ', text)  # Replace multiple spaces with single space
        text = '\n'.join(line for line in text.split('\n') if line.strip())  # Remove empty lines
        return text

class JobsCzScraper(JobBoardScraper):
    """
    Specific implementation for jobs.cz website.
    Inherits from JobBoardScraper and implements its abstract methods.
    """
    
    def __init__(self):
        """
        Initialize with base URL and search parameters.
        Currently only searches for Python jobs.
        """
        self.base_url = "https://www.jobs.cz/prace/"
        self.search_params = {"q[]": "python"}

    def extract_job_text(self, soup: BeautifulSoup) -> str:
        """
        Extracts job description from jobs.cz specific HTML structure.
        Removes unwanted elements like scripts, styles, nav, etc.
        Returns cleaned job description text.
        """
        content_div = soup.find('div', attrs={'data-jobad': 'body'})
        if not content_div:
            return ""
            
        # Remove unwanted HTML elements
        for element in content_div.find_all(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
            
        return self.clean_text(content_div.get_text(separator='\n', strip=True))

class JobScraper:
    """
    Main scraper class that coordinates the entire scraping process.
    Handles job scraping, data processing, and output to Google Docs.
    """
    
    def __init__(self):
        """
        Initialize scraper with JobsCzScraper instance and empty jobs list.
        Sets up Google Docs API connection.
        """
        self.scraper = JobsCzScraper()
        self.jobs: List[Dict] = []
        self.setup_google_docs()

    def setup_google_docs(self):
        """
        Sets up Google Docs API client using service account credentials.
        Credentials are loaded from environment variables.
        """
        credentials_dict = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT'))
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/documents']
        )
        self.docs_service = build('docs', 'v1', credentials=credentials)

    def fetch_page(self, url: str) -> BeautifulSoup:
        """
        Fetches a webpage and returns BeautifulSoup object.
        Uses custom headers to mimic browser request.
        Implements error handling and logging.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            logging.info(f"Fetching URL: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logging.error(f"Error fetching {url}: {str(e)}")
            return None

    def extract_job_details(self, job_item: BeautifulSoup) -> Optional[Dict]:
        """
        Extracts all relevant job details from a job listing:
        - Title
        - Company
        - Location
        - URL
        - Job ID
        - Full job description
        Returns dictionary with job details or None if extraction fails.
        """
        try:
            # Find job title
            title_elem = job_item.find('h2', class_='SearchResultCard__title')
            if not title_elem:
                logging.warning("No title element found in job listing")
                return None
            title = title_elem.get_text(strip=True)
            
            # Find job URL
            url_elem = title_elem.find('a', class_='link-primary')
            if not url_elem or 'href' not in url_elem.attrs:
                logging.warning("No URL element found in job listing")
                return None
            url = url_elem['href']
            if not url.startswith('http'):
                url = f"https://www.jobs.cz{url}"
                
            # Extract job ID from URL
            job_id = None
            id_match = re.search(r'/rpd/(\d+)/', url)
            if id_match:
                job_id = id_match.group(1)
            else:
                logging.warning(f"Could not extract job ID from URL: {url}")
            
            # Find company name
            company_elem = job_item.find('span', {'translate': 'no'})
            company = company_elem.get_text(strip=True) if company_elem else ""
            
            # Find location
            location_elem = job_item.find('li', {'data-test': 'serp-locality'})
            location = location_elem.get_text(strip=True) if location_elem else "Remote"
            
            # Get full job text from the detail page
            job_soup = self.fetch_page(url)
            job_text = ""
            if job_soup:
                job_text = self.scraper.extract_job_text(job_soup)
                if not job_text:
                    logging.warning(f"Could not find job description for {title} at {company}")
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'url': url,
                'job_id': job_id,
                'text': job_text
            }
            
        except Exception as e:
            logging.warning(f"Error extracting job details: {str(e)}")
            return None

    def get_total_pages(self) -> int:
        """
        Determines total number of pages with job listings.
        Handles pagination and checks for last page indicators:
        - "Page not available" message
        - Empty results
        - No results message
        Returns total number of pages found.
        """
        page = 1
        while True:
            url = f"{self.scraper.base_url}?q[]={self.scraper.search_params['q[]']}&page={page}"
            soup = self.fetch_page(url)
            
            # Check if page exists
            if not soup:
                logging.warning(f"Failed to fetch page {page}")
                break
            
            # Check for "page not available" message
            not_available = soup.find(string=lambda text: 'Zadaná stránka už není dostupná' in str(text) if text else False)
            if not_available:
                logging.info(f"Page {page} not available - reached end of listings")
                page -= 1  # Go back one page since this one isn't valid
                break
            
            # Check for job listings
            job_items = soup.find_all('article', class_='SearchResultCard')
            if not job_items:
                # Double check if we're on a "no results" page
                no_results = soup.find('div', class_='SearchNoResults')
                if no_results:
                    logging.info("No results found")
                    break
                # Also check for empty results container
                results_container = soup.find('div', class_='SearchResultList')
                if results_container and len(results_container.find_all('article')) == 0:
                    logging.info("Empty results container found")
                    break
                
            logging.info(f"Found {len(job_items)} jobs on page {page}")
            page += 1
            
            # Add a small delay between requests
            time.sleep(1)
        
        total_pages = page
        logging.info(f"Total pages found: {total_pages}")
        return total_pages

    def scrape_jobs(self):
        """
        Main scraping function that:
        1. Gets total number of pages
        2. Iterates through each page
        3. Extracts job listings from each page
        4. Processes each job listing
        Implements error handling and logging throughout.
        Returns True if any jobs were successfully scraped.
        """
        try:
            page = 1
            total_jobs_found = 0
            failed_jobs = 0
            
            # Get total number of pages first
            total_pages = self.get_total_pages()
            logging.info(f"Found {total_pages} pages to scrape")
            
            # Find total number of jobs from first page
            initial_url = f"{self.scraper.base_url}?q[]={self.scraper.search_params['q[]']}"
            initial_soup = self.fetch_page(initial_url)
            if not initial_soup:
                logging.error("Failed to fetch initial page")
                return False
            
            # Find total number of jobs
            total_count_elem = initial_soup.find('h1', class_='SearchHeader__title')
            if total_count_elem:
                try:
                    count = int(''.join(filter(str.isdigit, total_count_elem.text)))
                    logging.info(f"Total jobs found: {count}")
                except ValueError:
                    logging.warning("Could not parse total job count")
            
            # Scrape each page
            while page <= total_pages:
                url = f"{self.scraper.base_url}?q[]={self.scraper.search_params['q[]']}"
                if page > 1:
                    url += f"&page={page}"
                
                logging.info(f"Scraping page {page} of {total_pages}...")
                soup = self.fetch_page(url)
                if not soup:
                    logging.error(f"Failed to fetch page {page}")
                    page += 1
                    continue
                
                # Find all job listings on the page
                job_items = soup.find_all('article', class_='SearchResultCard')
                if not job_items:
                    logging.warning(f"No job items found on page {page}")
                    page += 1
                    continue
                
                logging.info(f"Found {len(job_items)} job items on page {page}")
                
                for job_item in job_items:
                    try:
                        job_details = self.extract_job_details(job_item)
                        if job_details:
                            self.jobs.append(job_details)
                            total_jobs_found += 1
                            logging.info(f"Scraped job {total_jobs_found}: {job_details['title']} at {job_details['company']}")
                        else:
                            failed_jobs += 1
                    except Exception as e:
                        logging.warning(f"Error scraping job on page {page}: {str(e)}")
                        failed_jobs += 1
                        continue
                
                # Add delay between pages to be nice to the server
                if page < total_pages:
                    time.sleep(2)
                page += 1

            logging.info(f"Successfully scraped {total_jobs_found} Python jobs across {page-1} pages")
            if failed_jobs > 0:
                logging.warning(f"Failed to scrape {failed_jobs} jobs")
            return total_jobs_found > 0

        except Exception as e:
            logging.error(f"Fatal error in scrape_jobs: {str(e)}")
            return False

    def create_markdown_content(self) -> str:
        """
        Creates formatted markdown content from scraped jobs.
        Includes:
        - Current timestamp
        - Total number of jobs
        - Formatted details for each job
        Returns formatted markdown string.
        """
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
        content = f"# Python pracovní nabídky\nPoslední aktualizace: {current_time}\nPočet nalezených nabídek: {len(self.jobs)}\n\n"

        for job in self.jobs:
            content += f"## {job['title']}\n"
            content += f"URL adresa: {job['url']}\n"
            content += f"ID: {job['job_id']}\n"
            content += f"Společnost: {job['company']}\n"
            content += f"Lokalita: {job['location']}\n"
            content += f"Text inzerátu:\n{job['text']}\n\n---\n\n"

        return content

    def update_google_doc(self):
        """
        Updates Google Doc with scraped job listings:
        1. Retrieves existing document
        2. Clears current content
        3. Inserts new markdown content
        Implements error handling and logging.
        Returns True if update was successful.
        """
        doc_id = os.getenv('GOOGLE_DOC_ID')
        if not doc_id:
            logging.error("Error: GOOGLE_DOC_ID not found in environment variables")
            return

        content = self.create_markdown_content()
        
        try:
            logging.info(f"Attempting to update Google Doc with ID: {doc_id}")
            logging.info(f"Number of jobs to update: {len(self.jobs)}")
            
            # Retrieve the document to get the current content length
            try:
                document = self.docs_service.documents().get(documentId=doc_id).execute()
                logging.info("Successfully retrieved document")
            except Exception as e:
                logging.error(f"Failed to retrieve document: {str(e)}")
                raise
                
            end_index = document.get('body', {}).get('content', [{}])[-1].get('endIndex', 1)
            logging.info(f"Document end index: {end_index}")

            # Clear the existing content
            requests = [{
                'deleteContentRange': {
                    'range': {
                        'startIndex': 1,
                        'endIndex': end_index - 1
                    }
                }
            }]

            # Insert new content
            requests.append({
                'insertText': {
                    'location': {'index': 1},
                    'text': content
                }
            })

            # Execute the update
            try:
                result = self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
                logging.info("Successfully updated Google Doc")
                return True
            except Exception as e:
                logging.error(f"Failed to update document content: {str(e)}")
                raise

        except Exception as e:
            logging.error(f"Error updating Google Doc: {str(e)}")
            return False

def main():
    """
    Main entry point of the script.
    Coordinates the entire process:
    1. Creates scraper instance
    2. Runs job scraping
    3. Updates Google Doc
    Implements error handling and proper exit codes.
    """
    try:
        scraper = JobScraper()
        if not scraper.scrape_jobs():
            logging.error("Failed to scrape any jobs")
            sys.exit(1)
        if not scraper.update_google_doc():
            logging.error("Failed to update Google Doc")
            sys.exit(1)
        logging.info("Script completed successfully")
    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 