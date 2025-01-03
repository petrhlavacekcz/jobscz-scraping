# Jobs.cz Python Job Scraper

Automated scraper for Python job listings from Jobs.cz, using BeautifulSoup for web scraping and Google Docs API for storing results.

## Features

- Scrapes Python job listings from Jobs.cz
- Uses BeautifulSoup and Requests for web scraping
- Stores results in a Google Doc
- Runs automatically via GitHub Actions

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Google Cloud Project:
   - Create a new project in Google Cloud Console
   - Enable Google Docs API
   - Create a Service Account and download the JSON key
   - Share your target Google Doc with the service account email

4. Set up GitHub repository secrets:
   - Go to your repository's Settings > Secrets and variables > Actions
   - Add the following secrets:
     - `GOOGLE_SERVICE_ACCOUNT`: Your service account JSON key
     - `GOOGLE_DOC_ID`: The ID of your Google Doc (from the URL)

5. Create a `.env` file locally with the same variables:
   ```
   GOOGLE_SERVICE_ACCOUNT='{"your":"service-account-json"}'
   GOOGLE_DOC_ID='your-doc-id'
   ```

## Running Locally

```bash
python scraper.py
```

## Deployment

The scraper is automatically run daily at 6:00 AM UTC via GitHub Actions. You can also trigger it manually:

1. Go to the Actions tab in your repository
2. Select "Run Jobs.cz Scraper" workflow
3. Click "Run workflow"

## License

MIT
