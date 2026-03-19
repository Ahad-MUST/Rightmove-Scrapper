"""
Rightmove Scraper - Browser Management
======================================
Handles Chrome WebDriver with aggressive timeout handling.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import time
import random
from typing import Optional
import config


class Browser:
    """Manages Chrome WebDriver with aggressive timeout handling."""

    def __init__(self, headless: bool = None, debug: bool = False):
        self.headless = headless if headless is not None else config.HEADLESS
        self.debug    = debug
        self.driver   = None
        self._setup_driver()

    def _setup_driver(self):
        """Set up Chrome with performance-oriented settings."""
        if self.debug:
            print("Setting up Chrome WebDriver...")

        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument('--headless=new')

        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument(
            f'--window-size={config.WINDOW_SIZE[0]},{config.WINDOW_SIZE[1]}'
        )
        chrome_options.add_argument(f'user-agent={config.USER_AGENT}')

        # Disable image loading to speed up page loads
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        service = Service(ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install())        
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        self.driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
        self.driver.implicitly_wait(config.IMPLICIT_WAIT)

        if self.debug:
            print("✓ Chrome initialised\n")

    def get_page(self, url: str, max_retries: int = None) -> Optional[str]:
        """
        Load a page and return its HTML source.

        On TimeoutException the page load is stopped and whatever has already
        loaded is returned (if it is large enough to be useful). Returns None
        only when every retry attempt fails to produce usable content.
        """
        if max_retries is None:
            max_retries = config.RETRY_ATTEMPTS

        for attempt in range(max_retries):
            try:
                if self.debug and attempt > 0:
                    print(f"        Retry {attempt + 1}/{max_retries}")

                self.driver.get(url)
                time.sleep(0.5)  # Let JS settle

                page_source = self.driver.page_source
                if len(page_source) < 1000:
                    if self.debug:
                        print(f"        ⚠️  Page too small ({len(page_source)} bytes)")
                    continue

                return page_source

            except TimeoutException:
                if self.debug:
                    print(f"        ⚠️  Timeout on attempt {attempt + 1}")

                # Stop the page load and try to recover whatever rendered
                try:
                    self.driver.execute_script("window.stop();")
                except WebDriverException:
                    pass

                try:
                    page_source = self.driver.page_source
                    if len(page_source) > 1000:
                        if self.debug:
                            print("        ✓ Got partial page after timeout")
                        return page_source
                except WebDriverException:
                    pass

                if attempt < max_retries - 1:
                    time.sleep(config.RETRY_DELAY)  # was wrongly using RETRY_ATTEMPTS

            except WebDriverException as e:
                if self.debug:
                    print(f"        ❌ WebDriver error: {type(e).__name__}")
                if attempt < max_retries - 1:
                    time.sleep(config.RETRY_DELAY)

        return None

    def human_delay(self, min_delay: float = None, max_delay: float = None):
        """Random delay to simulate human browsing behaviour."""
        if min_delay is None:
            min_delay = config.MIN_DELAY
        if max_delay is None:
            max_delay = config.MAX_DELAY
        time.sleep(random.uniform(min_delay, max_delay))

    def close(self):
        """Quit the browser and release resources."""
        if self.driver:
            try:
                self.driver.quit()
            except WebDriverException:
                pass
            finally:
                self.driver = None  # prevent double-quit attempts
            if self.debug:
                print("\n✓ Browser closed")