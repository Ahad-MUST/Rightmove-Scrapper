# Rightmove Production Scraper

A production-grade Rightmove property scraper with a web UI, authentication, and distributed task processing. Scrapes rental listings across UK cities and exports results to JSON, CSV, and Excel.

## Features

- Multi-location scraping: cities, areas, and filter combinations in one job
- Async task queue via Celery + Redis for concurrent scraping
- Real-time progress tracking in the browser
- Export to JSON, CSV, and styled Excel workbooks
- Authentication with session management
- Windows-native deployment with included startup scripts

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Flask 3.0 + Waitress |
| Task queue | Celery 5.3 + Redis |
| Browser automation | Selenium 4 (Chrome headless) |
| HTML parsing | BeautifulSoup4 |
| Data export | Pandas, Openpyxl |

## Prerequisites

- Python 3.9+
- Redis (running on `localhost:6379`)
- Google Chrome

## Setup

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**

   Edit `.env`:

   ```env
   SECRET_KEY=change_this_to_a_random_string
   FLASK_ENV=production
   REDIS_URL=redis://localhost:6379/0
   ADMIN_PASSWORD=your_password
   ```

3. **Start all services**

   ```batch
   start_services.bat
   ```

   This starts Redis, a Celery worker, and the Flask web server (port 5000) in sequence.

## Usage

1. Open `http://localhost:5000` in your browser
2. Log in with the admin credentials from `.env`
3. Select a city and one or more areas
4. Add filters (price range, bedrooms, furnishing, property type)
5. Set max properties per area and submit
6. Monitor progress in real time; download results when complete

## Project Structure

```
├── app.py              # Flask app, routes, Celery task
├── scraper.py          # Scraping orchestrator
├── extractor.py        # Data extraction (PAGE_MODEL JSON + HTML fallback)
├── browser.py          # Chrome WebDriver management
├── saver.py            # JSON / CSV / Excel export
├── config.py           # Timeouts, delays, browser settings
├── celery_config.py    # Celery worker configuration
├── data/
│   ├── cities.json     # Supported cities
│   └── city_areas.json # Area definitions with Rightmove slugs/region IDs
├── templates/          # Flask HTML templates
├── static/             # CSS and JavaScript
├── downloads/          # Scrape output (auto-created)
├── start_services.bat  # Start everything on Windows
└── diagnostics.bat     # System checks and troubleshooting
```

## API Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/` | GET | Yes | Main web UI |
| `/login` | GET, POST | No | Authentication |
| `/start_scraping` | POST | Yes | Submit a scraping job |
| `/status` | GET | Yes | Poll job progress |
| `/cancel_job` | POST | Yes | Cancel a running job |
| `/download/<type>` | GET | Yes | Download `json` or `xlsx` |
| `/health` | GET | No | Health check |

## Configuration

Key settings in `config.py`:

| Setting | Default | Description |
|---|---|---|
| Page load timeout | 8 sec | Max wait for page load |
| Request delay | 4–8 sec | Random delay between requests |
| Retry attempts | 2 | Retries per failed page |
| Max workers | 3 | Celery concurrency limit |
| Task timeout | 1 hour | Max Celery task duration |

## Troubleshooting

Run `diagnostics.bat` to check:
- Python and package installation
- Redis server status
- Port 5000 availability
- Chrome installation
- Windows Firewall rules

## Supported Locations

| City | Areas |
|---|---|
| London | Central, North, East, South, West + 50+ boroughs |
| Manchester | Zones + districts |
| Leeds | Zones + districts |
| Birmingham | Zones + districts |
