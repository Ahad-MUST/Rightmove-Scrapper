"""
Rightmove Scraper - Data Extractor
====================================
Extracts PAGE_MODEL JSON from page source (the key to reliability).
Falls back to HTML parsing when PAGE_MODEL is unavailable.
"""

import re
import json
from typing import Optional, Dict, List
from bs4 import BeautifulSoup


class DataExtractor:
    """Extracts data from Rightmove pages."""

    # ── Search-results page ───────────────────────────────────────────────────

    @staticmethod
    def extract_listing_urls(page_source: str) -> List[str]:
        """
        Extract property URLs from a search-results page.

        Tries two methods for robustness:
          1. BeautifulSoup anchor-tag scan (preferred)
          2. Raw-text regex fallback when Method 1 finds nothing
        """
        soup = BeautifulSoup(page_source, 'html.parser')
        urls: List[str] = []

        # Method 1: anchor tags whose href contains /properties/<id>
        for link in soup.find_all('a', href=re.compile(r'/properties/\d+')):
            match = re.search(r'/properties/(\d+)', link.get('href', ''))
            if match:
                clean_url = f"https://www.rightmove.co.uk/properties/{match.group(1)}"
                if clean_url not in urls:
                    urls.append(clean_url)

        # Method 2: raw-text regex (fallback)
        if not urls:
            for prop_id in re.findall(r'property[/-](\d{8,})', page_source, re.I):
                url = f"https://www.rightmove.co.uk/properties/{prop_id}"
                if url not in urls:
                    urls.append(url)

        return urls

    # ── Individual property page ──────────────────────────────────────────────

    @staticmethod
    def extract_page_model(page_source: str) -> Optional[Dict]:
        """
        Extract the PAGE_MODEL JSON object embedded by Rightmove in every
        property page.  Two regex patterns are tried for resilience.

        Returns the parsed dict, or None if not found / not parseable.
        """
        for pattern in (
            r'window\.PAGE_MODEL\s*=\s*(\{.*?\});',
            r'PAGE_MODEL\s*=\s*(\{.*?\});',
        ):
            match = re.search(pattern, page_source, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

        return None

    @staticmethod
    def extract_property_data(page_model: Dict) -> Optional[Dict]:
        """
        Parse a PAGE_MODEL dict into a clean property record.

        Returns None if page_model is falsy or parsing raises an exception.
        """
        if not page_model:
            return None

        try:
            prop_data = page_model.get('propertyData', {})

            return {
                'property_id':   prop_data.get('id'),
                'price':         DataExtractor._extract_price(prop_data),
                'agent_phone':   DataExtractor._extract_agent_phone(prop_data),
                'description':   prop_data.get('text', {}).get('description'),
                'key_features':  prop_data.get('keyFeatures', []),
                'address':       prop_data.get('address', {}).get('displayAddress'),
                'property_type': prop_data.get('propertySubType'),
                'bedrooms':      prop_data.get('bedrooms'),
            }

        except Exception as e:
            print(f"      ⚠️  Error parsing PAGE_MODEL: {e}")
            return None

    @staticmethod
    def extract_property_data_from_html(page_source: str, url: str) -> Optional[Dict]:
        """
        Fallback HTML parser used when PAGE_MODEL is unavailable.

        Extracts price, address, bedrooms, agent phone, description and key
        features using a cascade of BeautifulSoup + regex strategies.
        """
        try:
            soup = BeautifulSoup(page_source, 'html.parser')

            # Property ID from URL
            id_match = re.search(r'/properties/(\d+)', url)
            prop_id  = id_match.group(1) if id_match else None

            data: Dict = {
                'property_id':   prop_id,
                'price':         None,
                'agent_phone':   None,
                'description':   None,
                'key_features':  [],
                'address':       None,
                'property_type': None,
                'bedrooms':      None,
            }

            # ── Price ─────────────────────────────────────────────────────────
            for tag in ('span', 'div'):
                elem = soup.find(tag, class_=re.compile(r'price', re.I))
                if elem:
                    text = elem.get_text(strip=True)
                    if '£' in text:
                        data['price'] = text
                        break

            if not data['price']:
                m = re.search(r'£[\d,]+\s*(?:pcm|pw|per month|per week)',
                              page_source, re.I)
                if m:
                    data['price'] = m.group(0)

            # Deeper JSON / HTML class fallbacks for price
            if not data['price']:
                price_patterns = [
                    r'"price"[^}]*?"displayPrices"[^}]*?"displayPrice"\s*:\s*"([^"]+)"',
                    r'propertyHeaderPrice[^>]*>([^<]+)<',
                    r'<span[^>]*>(£[\d,]+\s*(?:pcm|pw|per month))</span>',
                ]
                for pat in price_patterns:
                    m = re.search(pat, page_source, re.I | re.DOTALL)
                    if m:
                        data['price'] = m.group(1).strip()
                        break

            # ── Address ───────────────────────────────────────────────────────
            address_elem = (
                soup.find('h1', class_=re.compile(r'address', re.I))
                or soup.find('address')
                or soup.find(itemprop='address')
            )
            if not address_elem:
                title_tag = soup.find('title')
                if title_tag:
                    title_text = title_tag.get_text()
                    m = re.match(r'^([^|]+?)\s+(?:to rent|for sale)', title_text, re.I)
                    if m:
                        addr = re.sub(r'\d+\s*bedroom\s*', '', m.group(1), flags=re.I).strip()
                        addr = re.sub(r'^\d+\s*bed\s*', '', addr, flags=re.I).strip()
                        if addr:
                            # Lightweight shim so get_text() works below
                            address_elem = type('_Shim', (), {'get_text': lambda self, strip=False: addr})()

            if address_elem:
                data['address'] = address_elem.get_text(strip=True)

            # ── Bedrooms ──────────────────────────────────────────────────────
            title_tag = soup.find('title')
            if title_tag:
                m = re.search(r'(\d+)\s*bed', title_tag.get_text(), re.I)
                if m:
                    data['bedrooms'] = m.group(1)

            # ── Agent phone ───────────────────────────────────────────────────
            tel_links = soup.find_all('a', href=re.compile(r'^tel:'))
            if tel_links:
                data['agent_phone'] = (
                    tel_links[0].get('href', '').replace('tel:', '').strip()
                )

            # ── Description ───────────────────────────────────────────────────
            desc_elem = (
                soup.find(itemprop='description')
                or soup.find('div', class_=re.compile(r'description', re.I))
            )
            if not desc_elem:
                heading = soup.find(string=re.compile(r'About this property', re.I))
                if heading:
                    parent = heading.find_parent(['div', 'section'])
                    if parent:
                        desc_elem = parent

            if desc_elem:
                desc_text = re.sub(r'\s+', ' ', desc_elem.get_text(strip=True))
                desc_text = re.sub(r'^About this property\s*', '', desc_text, flags=re.I)
                if len(desc_text) > 1000:
                    desc_text = desc_text[:1000] + '...'
                data['description'] = desc_text if len(desc_text) > 20 else None

            # JSON / meta-tag fallback for description
            if not data['description']:
                desc_patterns = [
                    r'"description"\s*:\s*"([^"]{50,500})"',
                    r'<meta[^>]*name="description"[^>]*content="([^"]{50,500})"',
                ]
                for pat in desc_patterns:
                    m = re.search(pat, page_source, re.I)
                    if m:
                        desc = m.group(1).strip().replace('&amp;', '&').replace('&quot;', '"')
                        if len(desc) > 20:
                            data['description'] = desc
                            break

            # ── Key features ──────────────────────────────────────────────────
            features_list = soup.find('ul', class_=re.compile(r'key.*feature|_1uI3IvdF', re.I))
            if features_list:
                for li in features_list.find_all('li')[:10]:
                    text = li.get_text(strip=True)
                    if len(text) > 5:
                        data['key_features'].append(text)

            return data

        except Exception as e:
            print(f"      ⚠️  Error parsing HTML: {e}")
            return None

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _extract_price(prop_data: Dict) -> Optional[str]:
        """Pull the display price out of the PAGE_MODEL propertyData block."""
        prices = prop_data.get('prices', {})
        if 'primaryPrice' in prices:
            return prices['primaryPrice']

        display_prices = prop_data.get('price', {}).get('displayPrices', [])
        if display_prices:
            return display_prices[0].get('displayPrice')

        return None

    @staticmethod
    def _extract_agent_phone(prop_data: Dict) -> Optional[str]:
        """Pull the agent phone number out of the PAGE_MODEL customer block."""
        customer = prop_data.get('customer', {})
        return (
            customer.get('branchPhone')
            or customer.get('contactTelephone')
        )