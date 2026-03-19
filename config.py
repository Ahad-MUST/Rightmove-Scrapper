"""
Rightmove Scraper - Configuration
==================================
"""

# Base URL
BASE_URL = "https://www.rightmove.co.uk"

# Timeouts (in seconds)
PAGE_LOAD_TIMEOUT = 8   # Kill page after 8 seconds
IMPLICIT_WAIT     = 2   # Wait 2 seconds for elements
RETRY_ATTEMPTS    = 2   # Retry each page this many times
RETRY_DELAY       = 3.0 # Seconds to wait between retries

# Delays between property requests
DEFAULT_DELAY = 3.0
MIN_DELAY     = 4.0
MAX_DELAY     = 8.0

# Browser settings
HEADLESS     = True
WINDOW_SIZE  = (1920, 1080)
USER_AGENT   = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)

# Scraping
DEFAULT_MAX_PROPERTIES = 10
PROGRESS_INTERVAL      = 5

# Output
DEFAULT_OUTPUT = 'rightmove_data'
JSON_INDENT    = 2