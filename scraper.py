"""
Rightmove Scraper - Main Scraper Class
========================================
Orchestrates the scraping process.
"""

import time
from typing import List, Dict, Optional
from browser import Browser
from extractor import DataExtractor
import config


class RightmoveScraper:
    """Orchestrates page loading, data extraction, and progress reporting."""

    def __init__(self, headless: bool = None, delay: float = None, debug: bool = False):
        # delay kept as a parameter for CLI compatibility but the actual
        # inter-request delay is controlled by Browser.human_delay()
        self.debug = debug

        self.browser   = Browser(headless=headless, debug=debug)
        self.extractor = DataExtractor()

        self.scraped_count = 0
        self.skipped_count = 0

    def build_search_url(self, location: str, property_type: str = "to-rent") -> str:
        """Build a Rightmove search URL from a plain-text location name."""
        slug = location.replace(" ", "-")
        if location.islower():
            slug = location.title().replace(" ", "-")
        return f"{config.BASE_URL}/property-{property_type}/{slug}.html?sortType=6"

    def scrape_property(self, url: str) -> Optional[Dict]:
        """
        Scrape a single property page.

        Tries PAGE_MODEL JSON extraction first (fast, complete), then falls
        back to HTML parsing if PAGE_MODEL is absent.
        """
        page_source = self.browser.get_page(url)
        if not page_source:
            if self.debug:
                print("      ⚠️  Failed to load page")
            return None

        page_model = self.extractor.extract_page_model(page_source)

        if page_model:
            if self.debug:
                print("      → Using PAGE_MODEL extraction")
            data = self.extractor.extract_property_data(page_model)
        else:
            if self.debug:
                print("      → PAGE_MODEL not found, using HTML parsing")
            data = self.extractor.extract_property_data_from_html(page_source, url)

        if not data:
            if self.debug:
                print("      ⚠️  Failed to extract data")
            return None

        data['url']        = url
        data['scraped_at'] = time.strftime('%Y-%m-%d %H:%M:%S')

        price = data.get('price') or 'N/A'
        phone = data.get('agent_phone')
        print(f"      ✓ {price}")
        if phone:
            print(f"        📞 {phone}")

        return data

    def scrape(self, start_url: str, max_properties: int = None) -> List[Dict]:
        """
        Scrape a search-results page then each individual property.

        Args:
            start_url:      Rightmove search-results URL.
            max_properties: Cap on how many properties to visit.

        Returns:
            List of property dicts.
        """
        if max_properties is None:
            max_properties = config.DEFAULT_MAX_PROPERTIES

        print("=" * 70)
        print("RIGHTMOVE SCRAPER — PAGE_MODEL EXTRACTION")
        print("=" * 70)

        print("\nStep 1: Loading search results...")
        page_source = self.browser.get_page(start_url)
        if not page_source:
            print("❌ Failed to load search page")
            return []

        property_urls = self.extractor.extract_listing_urls(page_source)

        if self.debug:
            print(f"  → Page size: {len(page_source):,} bytes")
            print(f"  → Found {len(property_urls)} URLs before cap")

        property_urls = property_urls[:max_properties]
        print(f"  ✓ Scraping {len(property_urls)} properties\n")

        if not property_urls:
            print("❌ No properties found on search page")
            return []

        print(f"Step 2: Scraping {len(property_urls)} properties...")
        print("=" * 70)

        all_properties: List[Dict] = []

        for i, url in enumerate(property_urls, 1):
            print(f"\n[{i}/{len(property_urls)}] {url.split('/')[-1]}")
            try:
                prop = self.scrape_property(url)
                if prop:
                    all_properties.append(prop)
                    self.scraped_count += 1
                else:
                    self.skipped_count += 1
                    print("      ⚠️  SKIPPED")

                if i % config.PROGRESS_INTERVAL == 0:
                    print(
                        f"    Progress: {self.scraped_count} scraped, "
                        f"{self.skipped_count} skipped ({i}/{len(property_urls)})"
                    )

                if i < len(property_urls):
                    self.browser.human_delay()

            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user")
                break
            except Exception as e:
                print(f"      ❌ Error: {type(e).__name__}")
                self.skipped_count += 1
                if self.debug:
                    import traceback
                    traceback.print_exc()

        print(f"\n\n{'=' * 70}")
        print(f"COMPLETED: {self.scraped_count} scraped, {self.skipped_count} skipped")
        print("=" * 70)

        return all_properties

    def close(self):
        """Close the browser."""
        self.browser.close()