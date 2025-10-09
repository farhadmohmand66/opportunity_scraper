
# Opportunity Scraper 🎯

A comprehensive web scraping system that extracts opportunities (volunteering, events, scholarships, etc.) from multiple websites, specifically filtering for Bulgaria-eligible opportunities.

## 📁 Project Structure

```
opportunity_scraper/
├── scrapers/
│   ├── __init__.py
│   ├── opportunit4u_scraper.py
│   ├── european_youth_scraper.py
│   ├── smokinya_scraper.py
│   └── eurodesk_scraper.py
├── data/
│   ├── opportunit4u_data.json
│   ├── european_youth_portal_bulgaria_eligible.json
│   ├── smokinya_bulgaria_eligible.json
│   └── eurodesk_learning.json
├── config/
│   ├── __init__.py
│   ├── config.py
│   ├── category_keywords.json
│   ├── country.json
│   └── world_cities.json
├── main.py
├── requirements.txt
├── translator.py
└── README.md
```

## 🚀 Quick Start

### ⚙️ Installation

Clone the repo and install dependencies:

```bash
# git clone https://github.com/yourusername/opportunity_scraper.git
cd opportunity_scraper
pip install -r requirements.txt
```

### Configuration

In `config/config.py`, set your OpenAI API key:

```python
OPENAI_API_KEY = "your-openai-api-key-here"
```

### Running the Scrapers

Run All Scrapers:

```bash
python main.py
```
### or run individual scraper then run merg_all_json.py

Run specific scraper:

```bash
python scrapers/eurodesk_scraper.py
python scrapers/european_youth_scraper.py
python scrapers/opportunit4u_scraper.py
python scrapers/smokinya_scraper.py
```
Incase you run invidual srapers then you have to run the merg_all_json.py

```
python merge_all_json.py

```

## 🛠️ Scrapers Overview

1. **Eurodesk Scraper**
   - **Website:** [Eurodesk Learning](https://programmes.eurodesk.eu/learning)
   - **Features:**
     - Filters by Bulgaria eligibility
     - Extracts online/onsite opportunities
     - Uses category keyword matching
     - Skips "UPCOMING" opportunities
   - **Output:** `data/eurodesk_learning.json`

2. **European Youth Portal Scraper**
   - **Website:** [European Youth Portal](https://youth.europa.eu/go-abroad/volunteering/opportunities_en)
   - **Features:**
     - Specifically for volunteering opportunities
     - Bulgaria eligibility filtering
     - Load more functionality
     - Automatic category detection
   - **Output:** `data/european_youth_portal_bulgaria_eligible.json`

3. **Opportunit4u Scraper**
   - **Website:** [Opportunit4u](https://www.opportunit4u.com/)
   - **Features:**
     - Load more pagination
     - Bulgaria eligibility based on description analysis
     - Location extraction from titles
     - Multiple opportunity types
   - **Output:** `data/opportunit4u_data.json`

4. **Smokinya Scraper**
   - **Website:** [Smokinya](https://smokinya.com/)
   - **Features:**
     - Uses OpenAI GPT for intelligent data extraction
     - Advanced entity recognition
     - Automatic category classification
     - Smart location detection
   - **Output:** `data/smokinya_bulgaria_eligible.json`

---

## 🚀 Features

- Scrapes opportunities from:
  - [Opportunit4u](https://www.opportunit4u.com/)
  - [European Youth Portal](https://youth.europa.eu/)
  - [Smokinya Foundation](https://smokinya.com/)
  - [Eurodesk Learning](https://programmes.eurodesk.eu/learning)
  
- Normalizes and merges different schemas into a single dataset.
- Outputs a combined JSON file: **`data/all_opportunities.json`**

---

## Proposed Unified Schema

```json
{
  "postNo": 1,
  "title": "string",
  "title_bg": "string",
  "city": "string or null",
  "country": "string or null",
  "description": "string",
  "description_bg": "string",
  "validUntil": "string (date or CURRENT)",
  "originalDate": raw_date,
  "type": "string",
  "modeOfWork": "string",
  "categories": ["list of strings"],
  "applicationUrl": "string",
  "bannerImage": "string",
  "bulgariaEligible": true/false (optional, default false)
  "source": source
}
```

### Field Descriptions:
- **postNo:** Sequential number of the opportunity
- **title:** Opportunity title/name
- **title_bg:** Opportunity title/name in Bulgarian language
- **city:** Location city (extracted from text)
- **country:** Location country (extracted from text)
- **description:** Full opportunity description
- **description_bg:** Full opportunity description bulgarian language
- **validUntil:** Application deadline date
- **originalDate"** raw_date,
- **type:** Opportunity type (volunteering, event, scholarship, etc.)
- **modeOfWork:** remote, on-site, or hybrid
- **categories:** List of relevant categories
- **applicationUrl:** URL to apply/learn more
- **bannerImage:** URL to the banner Image
- **bulgariaEligible:** Boolean indicating Bulgaria eligibility
- **sourc:** the thd dns of the website

### 🎯 Opportunity Types
- **volunteering:** Volunteer programs and opportunities
- **event:** Conferences, workshops, seminars
- **scholarship:** Funding and financial aid
- **competition:** Contests and challenges
- **exchange:** Cultural and youth exchanges
- **erasmus:** Erasmus+ programs
- **training:** Skill development programs
- **internship:** Professional internships

### 🏢 Categories
The system recognizes these categories:
- Programming, Business, Marketing, Journalism
- Trade, Psychology, Cinema, Finance
- Design, Music, Social Causes, Medicine
- Ecology, Languages, Career Guidance, Science
- Politics, Architecture, Health, Environment

## ⚙️ Configuration Files

### `category_keywords.json`
```json
{
  "Programming": ["programming", "coding", "software", "developer"],
  "Business": ["business", "entrepreneurship", "startup"],
  ...
}
```

### `country.json`
```json
{
  "countries": ["Bulgaria", "Germany", "France", ...]
}
```

### `world_cities.json`
```json
{
  "cities": ["Sofia", "Berlin", "Paris", ...]
}
```

## 🔧 Technical Details

### Dependencies
- **selenium:** Web browser automation
- **undetected-chromedriver:** Anti-detection Chrome driver
- **openai:** AI-powered data extraction (Smokinya scraper)
- **beautifulsoup4:** HTML parsing (backup)

### Browser Requirements
- Chrome browser installed
- Automatic ChromeDriver management via undetected-chromedriver

### Error Handling
- Individual scraper failures don't stop the entire system
- Detailed error logging for debugging
- Automatic retry mechanisms

## 🚨 Important Notes
- **CAPTCHA Handling:** Eurodesk may show CAPTCHA - manual solving required
- **Rate Limiting:** Built-in delays between requests to be respectful
- **API Key:** OpenAI API key required for Smokinya scraper
- **Browser Windows:** Scrapers open visible browser windows for interaction

## 📈 Output Management
- Each scraper saves to its own JSON file
- Data is automatically deduplicated
- Only Bulgaria-eligible opportunities are saved
- Consistent data structure across all sources

## 🆘 Troubleshooting
### Common Issues:
- **Import errors:** Make sure you're in the project root directory
- **Chrome not found:** Install Google Chrome browser
- **API key errors:** Check `config/config.py` file exists with a valid OpenAI key
- **CAPTCHA blocks:** Manually solve CAPTCHA when the browser opens
