# Jobs.cz Python Job Scraper

Automated scraper for Python job listings from Jobs.cz. The scraper runs daily via GitHub Actions and updates a Google Doc with the latest job listings.

## Features

- Scrapes Python job listings from Jobs.cz
- Extracts detailed job information including title, company, location, and full description
- Stores results in a Google Doc for easy access
- Runs automatically every day at 6:00 AM UTC via GitHub Actions
- Handles errors gracefully and provides logging

## Prerequisites

- GitHub account
- Google Cloud account (free tier is sufficient)
- Python 3.12 or higher (for local development)

## Setup Guide

### 1. Google Cloud Setup

1. Create a new Google Cloud Project:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Click "New Project" and give it a name
   - Note down the Project ID

2. Enable Google Docs API:
   - In your project, go to "APIs & Services" > "Library"
   - Search for "Google Docs API"
   - Click "Enable"

3. Create a Service Account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the service account details (name and description)
   - For the role, select "Editor" under "Basic"
   - Click "Done"

4. Generate Service Account Key:
   - In the service account list, click on your newly created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create New Key"
   - Choose JSON format
   - Download the key file (it will be used later)

5. Prepare Google Doc:
   - Create a new Google Doc where you want the job listings to appear
   - Share the document with the service account email (found in the downloaded JSON)
   - Copy the document ID from the URL (it's the long string between /d/ and /edit)
     Example: `https://docs.google.com/document/d/[THIS-IS-YOUR-DOC-ID]/edit`

### 2. GitHub Repository Setup

1. Fork or clone this repository

2. Set up GitHub Secrets:
   - Go to your repository's Settings > Secrets and variables > Actions
   - Add two new repository secrets:
     1. `GOOGLE_SERVICE_ACCOUNT`:
        - Open the downloaded JSON key file
        - Copy the entire contents
        - Paste as the secret value
     2. `GOOGLE_DOC_ID`:
        - Paste your Google Doc ID from step 5 above

3. The GitHub Actions workflow is already configured to run daily at 6:00 AM UTC

### 3. Local Development Setup

If you want to run the scraper locally:

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/jobscz-scraping.git
   cd jobscz-scraping
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file:
   ```
   GOOGLE_SERVICE_ACCOUNT='{"paste":"your-service-account-json-here"}'
   GOOGLE_DOC_ID='your-doc-id'
   ```

5. Run the scraper:
   ```bash
   python scraper.py
   ```

## Usage

### GitHub Actions (Automated)

The scraper runs automatically every day at 6:00 AM UTC. You can also trigger it manually:

1. Go to the Actions tab in your repository
2. Select "Run Jobs.cz Scraper" workflow
3. Click "Run workflow"

The workflow will:
- Run the scraper
- Update your Google Doc with the latest job listings
- Log any errors or issues

### Local Usage

When running locally, the scraper will:
1. Fetch all Python job listings from Jobs.cz
2. Parse the job details including full descriptions
3. Update your specified Google Doc
4. Create an error.log file with execution details

## Troubleshooting

1. If the workflow fails:
   - Check the Actions tab for error messages
   - Verify your GitHub secrets are correctly set
   - Ensure your Google Doc is shared with the service account

2. If the Google Doc isn't updating:
   - Verify the service account email has edit access to the document
   - Check that the document ID is correct
   - Look for error messages in the Actions logs

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT
