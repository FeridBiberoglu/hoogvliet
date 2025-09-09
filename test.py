import time
import json
import re
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urljoin
import logging
import requests 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup, Tag
import concurrent.futures

CONFIG = {
    "base_url": "https://www.hoogvliet.com/",
    "initial_url": "https://www.hoogvliet.com/INTERSHOP/web/WFS/org-webshop-Site/nl_NL/-/EUR/ViewStandardCatalog-Browse?CategoryName=aanbiedingen&CatalogID=schappen",
    "headless": True,
    "timeout": 20,
    "max_child_workers": 2,
    "child_request_delay": 1,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class HoogvlietScraper:
    def __init__(self, headless=True):
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument(f"user-agent={CONFIG['user_agent']}")
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option('useAutomationExtension', False)
        self.driver = None

    def start_driver(self):
        self.driver = webdriver.Chrome(options=self.options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return self.driver

    def scroll_to_load_products(self, max_scrolls=50, wait_time=2):
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scrolls = 0
        no_change_count = 0
        while scrolls < max_scrolls:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            if no_change_count == 0:
                try:
                    product_list_element = self.driver.find_element(By.CSS_SELECTOR, 'div.product-list.row')
                    self.driver.execute_script("arguments[0].scrollIntoView(false);", product_list_element)
                except NoSuchElementException:
                    logging.warning("Could not find product list element to scroll to. Breaking.")
                    break
            elif no_change_count == 1:
                logging.info("Page height hasn't changed. Scrolling down 200 pixels.")
                self.driver.execute_script("window.scrollBy(0, 200);")
            elif no_change_count == 2:
                logging.info("Page height hasn't changed. Scrolling up 400 pixels.")
                self.driver.execute_script("window.scrollBy(0, -400);")
            time.sleep(wait_time)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                no_change_count += 1
                if no_change_count >= 3:
                    logging.info("Page height hasn't changed after nudging. Assuming all products are loaded.")
                    break
            else:
                no_change_count = 0
            scrolls += 1
        logging.info(f"Finished scrolling after {scrolls} attempts.")

    def extract_product_info(self, product_element):
        product_data = {}
        try:
            track_click_attr = product_element.get_attribute('data-track-click')
            if track_click_attr:
                track_data = json.loads(track_click_attr)
                product_data['id'] = track_data.get('products', [{}])[0].get('id')
                product_data['brand'] = track_data.get('products', [{}])[0].get('brand')
        except Exception:
            product_data['id'], product_data['brand'] = None, None
        try:
            name_elem = product_element.find_element(By.CSS_SELECTOR, '.product-title h3')
            product_data['name'] = name_elem.text.strip()
        except: product_data['name'] = 'N/A'
        try:
            price_now_elem = product_element.find_element(By.CSS_SELECTOR, '.non-strikethrough')
            product_data['price_now_raw'] = price_now_elem.get_attribute('innerHTML')
        except: product_data['price_now_raw'] = None
        try:
            price_was_elem = product_element.find_element(By.CSS_SELECTOR, '.strikethrough')
            product_data['price_was_raw'] = price_was_elem.get_attribute('innerHTML')
        except: product_data['price_was_raw'] = None
        try:
            promo_elem = product_element.find_element(By.CSS_SELECTOR, '.promotion-short-title')
            product_data['promotion'] = promo_elem.text.strip()
        except: product_data['promotion'] = None
        try:
            img_elem = product_element.find_element(By.CSS_SELECTOR, 'img.product-image')
            product_data['image_url'] = img_elem.get_attribute('src')
        except: product_data['image_url'] = 'N/A'
        try:
            link_elem = product_element.find_element(By.CSS_SELECTOR, 'a.product-title, .product-image-container a')
            product_data['source_url'] = link_elem.get_attribute('href')
        except: product_data['source_url'] = 'N/A'
        try:
            desc_elem = product_element.find_element(By.CSS_SELECTOR, '.Short-Description')
            product_data['description'] = desc_elem.text.strip()
        except: product_data['description'] = None
        product_data['child_page_url'] = None
        try:
            parent_link_elem = product_element.find_element(By.CSS_SELECTOR, '.promotion-btn a.btn')
            product_data['child_page_url'] = parent_link_elem.get_attribute('href')
        except NoSuchElementException:
            pass
        return product_data

    def scrape_page(self, url: str, max_scrolls: int = 50) -> Tuple[List[Dict[str, Any]], List[Dict]]:
        self.driver = self.start_driver()
        products_on_page = []
        cookies = []
        try:
            logging.info(f"Loading page via Selenium: {url}")
            self.driver.get(url)
            try:
                WebDriverWait(self.driver, CONFIG['timeout']).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.product-list-item')))
            except TimeoutException:
                logging.warning(f"Timeout waiting for '.product-list-item' on page: {url}. Skipping.")
                return [], []

            cookies = self.driver.get_cookies()
            logging.info(f"Extracted {len(cookies)} cookies from the browser session.")
            self.scroll_to_load_products(max_scrolls=max_scrolls)
            
            logging.info("Extracting product information...")
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, '.product-list-item')
            
            for element in product_elements:
                product_info = self.extract_product_info(element)
                
                if product_info and product_info.get('id'):
                    products_on_page.append(product_info)

            logging.info(f"Successfully scraped {len(products_on_page)} raw products from {url}")
            return products_on_page, cookies
        except Exception as e:
            logging.error(f"An unexpected error occurred during Selenium scraping of {url}: {e}", exc_info=True)
            return [], []
        finally:
            if self.driver:
                self.driver.quit()


class DataNormalizer:
    def __init__(self, base_url: str):
        self.base_url = base_url
        
    def _normalize_text(self, text: Optional[str]) -> Optional[str]:
        if not text or not text.strip(): return None
        return re.sub(r'\s+', ' ', text).strip()

    def _normalize_price(self, raw_price: Optional[str]) -> Optional[str]:
        if not raw_price: return None
        soup = BeautifulSoup(raw_price, 'html.parser')
        euros_elem = soup.select_one('.price-euros span')
        cents_elem = soup.select_one('.price-cents sup')
        if euros_elem and cents_elem:
            euros = self._normalize_text(euros_elem.text)
            cents = self._normalize_text(cents_elem.text)
            return f"{euros}.{cents}"
        price_value_elem = soup.select_one('.kor-product-sale-price-value')
        if price_value_elem:
             cleaned_text = self._normalize_text(price_value_elem.text).replace(',', '.')
             match = re.search(r'(\d+\.\d{2})', cleaned_text)
             return match.group(1) if match else None
        cleaned_text = self._normalize_text(soup.text).replace(',', '.')
        match = re.search(r'(\d+\.\d{2})', cleaned_text)
        return match.group(1) if match else None

    def _parse_date_range(self, date_str: str) -> Tuple[Optional[str], Optional[str]]:
        month_map = {'januari': 1, 'februari': 2, 'maart': 3, 'april': 4, 'mei': 5, 'juni': 6, 'juli': 7, 'augustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'december': 12}
        try:
            date_part = date_str.split('|')[1].strip()
            start_str, end_str = date_part.split(' - ')
            current_year = datetime.now().year
            start_day, start_month_name = start_str.split()
            start_month = month_map[start_month_name.lower()]
            start_date = datetime(current_year, start_month, int(start_day)).date()
            end_day, end_month_name = end_str.split()
            end_month = month_map[end_month_name.lower()]
            end_date = datetime(current_year, end_month, int(end_day)).date()
            return start_date.isoformat(), end_date.isoformat()
        except Exception:
            return None, None

    def process(self, raw_products: List[Dict], timeframe_info: Dict) -> List[Dict]:
        normalized_list = []
        for raw in raw_products:
            record = {
                "id": raw.get('id'),
                "title": self._normalize_text(raw.get('name')),
                "description": self._normalize_text(raw.get('description')),
                "promotion": self._normalize_text(raw.get('promotion')),
                "price_now": self._normalize_price(raw.get('price_now_raw')),
                "price_was": self._normalize_price(raw.get('price_was_raw')),
                "image_url": urljoin(self.base_url, raw.get('image_url')) if raw.get('image_url') else None,
                "source_url": urljoin(self.base_url, raw.get('source_url')) if raw.get('source_url') else None,
                "child_page_url": urljoin(self.base_url, raw.get('child_page_url')) if raw.get('child_page_url') else None,
                "start_date": timeframe_info.get('start_date'),
                "end_date": timeframe_info.get('end_date'),
                "child_products": []
            }
            normalized_list.append(record)
        return normalized_list

def get_timeframe_urls(initial_url: str) -> Dict[str, Dict]:
    logging.info("--- Getting all timeframe URLs ---")
    scraper = HoogvlietScraper(headless=True)
    driver = scraper.start_driver()
    base_url = "https://www.hoogvliet.com/INTERSHOP/web/WFS/org-webshop-Site/nl_NL/-/EUR/ViewStandardCatalog-Browse"
    urls = {}
    try:
        driver.get(initial_url)
        wait = WebDriverWait(driver, CONFIG['timeout'])
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'input.filter-checkbox[data-document-location]')))
        normalizer = DataNormalizer(CONFIG['base_url'])
        current_input = driver.find_element(By.CSS_SELECTOR, 'input.filter-checkbox:checked')
        current_url = current_input.get_attribute('data-document-location')
        current_label = driver.find_element(By.CSS_SELECTOR, f"label[for='{current_input.get_attribute('id')}']").text
        start_date, end_date = normalizer._parse_date_range(current_label)
        urls['current'] = { "url": base_url + "?" + current_url.split('?')[-1], "start_date": start_date, "end_date": end_date }
        coming_input = driver.find_element(By.CSS_SELECTOR, 'input.filter-checkbox:not(:checked)')
        coming_url = coming_input.get_attribute('data-document-location')
        coming_label = driver.find_element(By.CSS_SELECTOR, f"label[for='{coming_input.get_attribute('id')}']").text
        start_date, end_date = normalizer._parse_date_range(coming_label)
        urls['coming'] = { "url": base_url + "?" + coming_url.split('?')[-1], "start_date": start_date, "end_date": end_date }
        logging.info(f"Found {len(urls)} timeframe URLs to scrape.")
        return urls
    except Exception as e:
        logging.error(f"Error getting timeframe URLs: {e}")
        return {}
    finally:
        if driver:
            driver.quit()

def extract_product_info_from_soup(product_element: Tag) -> Dict:
    product_data = {}
    try:
        track_click_attr = product_element.get('data-track-click')
        if track_click_attr:
            track_data = json.loads(track_click_attr)
            product_info = track_data.get('products', [{}])[0]
            product_data['id'] = product_info.get('id')
            product_data['brand'] = product_info.get('brand')
    except (json.JSONDecodeError, IndexError, KeyError):
        product_data['id'], product_data['brand'] = None, None
    name_elem = product_element.select_one('.product-title h3')
    product_data['name'] = name_elem.text.strip() if name_elem else 'N/A'
    price_now_elem = product_element.select_one('.non-strikethrough')
    price_was_elem = product_element.select_one('.strikethrough')
    if price_was_elem:
        product_data['price_now_raw'] = str(price_now_elem) if price_now_elem else None
        product_data['price_was_raw'] = str(price_was_elem)
    else:
        standard_price_container = product_element.select_one('.kor-product-sale-price')
        product_data['price_now_raw'] = str(standard_price_container) if standard_price_container else None
        product_data['price_was_raw'] = None
    promo_elem = product_element.select_one('.promotion-short-title')
    product_data['promotion'] = promo_elem.text.strip() if promo_elem else None
    img_elem = product_element.select_one('img.product-image')
    product_data['image_url'] = img_elem.get('src') if img_elem else 'N/A'
    link_elem = product_element.select_one('a.product-title, .product-image-container a')
    product_data['source_url'] = link_elem.get('href') if link_elem else 'N/A'
    desc_elem = product_element.select_one('.Short-Description')
    product_data['description'] = desc_elem.text.strip() if desc_elem else None
    parent_link_elem = product_element.select_one('.promotion-btn a.btn')
    product_data['child_page_url'] = parent_link_elem.get('href') if parent_link_elem else None
    return product_data

def scrape_child_page_worker(child_url: str, parent_info: Dict, cookies: List[Dict]) -> List[Dict]:
    try:
        time.sleep(CONFIG['child_request_delay'])
        
        session = requests.Session()
        session.headers.update({"User-Agent": CONFIG['user_agent']})
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        logging.info(f"Loading page via Requests: {child_url}")
        response = session.get(child_url, timeout=CONFIG['timeout'])
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        product_elements = soup.select('.product-list-item')

        if not product_elements:
            logging.warning(f"No product items found on child page: {child_url}")
            return []
        
        raw_products = [extract_product_info_from_soup(elem) for elem in product_elements]
        
        normalizer = DataNormalizer(CONFIG['base_url'])
        timeframe_info = {
            "start_date": parent_info.get('start_date'),
            "end_date": parent_info.get('end_date')
        }
        normalized_children = normalizer.process(raw_products, timeframe_info)
        return normalized_children
    except requests.exceptions.RequestException as e:
        logging.error(f"Worker for child URL {child_url} failed with a network error: {e}")
        return []
    except Exception as e:
        logging.error(f"Worker for child URL {child_url} failed with an unexpected error: {e}", exc_info=True)
        return []

def scrape_child_urls(normalized_products: List[Dict], cookies: List[Dict]) -> List[Dict]:
    products_with_children = {
        prod['id']: prod for prod in normalized_products if prod.get('child_page_url')
    }

    if not products_with_children:
        logging.info("No child URLs found to scrape.")
        return normalized_products

    logging.info(f"Found {len(products_with_children)} parent products with child URLs. Starting concurrent scraping.")
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG['max_child_workers']) as executor:
        future_to_parent_id = {
            executor.submit(scrape_child_page_worker, parent['child_page_url'], parent, cookies): parent_id
            for parent_id, parent in products_with_children.items()
        }

        for future in concurrent.futures.as_completed(future_to_parent_id):
            parent_id = future_to_parent_id[future]
            try:
                child_products_data = future.result()
                if child_products_data:
                    for parent_product in normalized_products:
                        if parent_product['id'] == parent_id:
                            parent_product['child_products'].extend(child_products_data)
                            logging.info(f"Added {len(child_products_data)} child products to parent ID {parent_id}.")
                            break
            except Exception as exc:
                logging.error(f"Child page future for parent ID {parent_id} generated an exception: {exc}")

    return normalized_products

def scrape_and_process_worker(url: str, info: Dict):
    scraper = HoogvlietScraper(headless=CONFIG['headless'])
    raw_data, cookies = scraper.scrape_page(url, max_scrolls=200)

    if not raw_data:
        return []
        
    normalizer = DataNormalizer(CONFIG['base_url'])
    normalized_products = normalizer.process(raw_data, info)
    
    products_with_children = scrape_child_urls(normalized_products, cookies)
    return products_with_children


def main():
    start_time = time.time()
    initial_url = CONFIG['initial_url']
    
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"Created directory: {output_dir}")

    urls_to_scrape = get_timeframe_urls(initial_url)
    if not urls_to_scrape:
        print("No urls to scrape")
        return
    total_products_scraped = 0
    error_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_to_key = {executor.submit(scrape_and_process_worker, info['url'], info): key for key, info in urls_to_scrape.items()}
        
        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            try:
                products = future.result()
                if products:
                    parent_count = len(products)
                    child_count = sum(len(p.get('child_products', [])) for p in products)
                    total_products_scraped += (parent_count + child_count)
                    
                    filename = os.path.join(output_dir, f"{key}_offers.json")
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(products, f, ensure_ascii=False, indent=2)
                    logging.info(f"Saved {parent_count} parent products (with {child_count} children) to {filename}")
            except Exception as exc:
                logging.error(f'{key} offers generated an exception: {exc}')
                error_count += 1
    duration = time.time() - start_time
    logging.info(f"\n--- SCRAPING SUMMARY ---")
    logging.info(f"Total products scraped (including children): {total_products_scraped}")
    logging.info(f"Total errors encountered: {error_count}")
    logging.info(f"Total duration: {duration:.2f} seconds")

if __name__ == "__main__":
    main()