import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import pandas as pd

class HoogvlietScraper:
    def __init__(self, headless=True):
        """Initialize the scraper with Chrome options"""
        self.options = webdriver.ChromeOptions()
        if headless:
            self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option('useAutomationExtension', False)
        self.driver = None
        self.products = []
        
    def start_driver(self):
        """Start the Chrome driver"""
        self.driver = webdriver.Chrome(options=self.options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def scroll_to_load_products(self, max_scrolls=50, wait_time=2):
        """
        Scroll down by repeatedly bringing the product list container into view,
        which is a more reliable way to trigger infinite scroll.
        """
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scrolls = 0
        no_change_count = 0
        
        while scrolls < max_scrolls:
            try:
                product_list_element = self.driver.find_element(By.CSS_SELECTOR, 'div.product-list.row')
                self.driver.execute_script("arguments[0].scrollIntoView(false);", product_list_element)
                print("Scrolled product list into view...")
                
            except NoSuchElementException:
                print("Could not find the product list element to scroll to. Breaking.")
                break
            time.sleep(wait_time)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                no_change_count += 1
                if no_change_count >= 3:
                    print("Page height hasn't changed after 3 scrolls. Assuming all products are loaded.")
                    break
            else:
                no_change_count = 0
            
            last_height = new_height
            scrolls += 1
            product_count = len(self.driver.find_elements(By.CSS_SELECTOR, '.product-tile'))
            print(f"Scroll {scrolls}: Found {product_count} products so far...")

        print(f"Finished scrolling after {scrolls} attempts.")   
            
    def extract_product_info(self, product_element):
        """Extract information from a single product element"""
        try:
            product_data = {}
            try:
                name_elem = product_element.find_element(By.CSS_SELECTOR, '.product-title, .product-name, h3, h4')
                product_data['name'] = name_elem.text.strip()
            except:
                product_data['name'] = 'N/A'
            try:
                price_selectors = [
                    '.product-price',
                    '.price',
                    '.current-price',
                    '[class*="price"]',
                    '.product-tile__price'
                ]
                price_text = None
                for selector in price_selectors:
                    try:
                        price_elem = product_element.find_element(By.CSS_SELECTOR, selector)
                        price_text = price_elem.text.strip()
                        if price_text:
                            break
                    except:
                        continue
                product_data['price'] = price_text if price_text else 'N/A'
            except:
                product_data['price'] = 'N/A'
            try:
                discount_elem = product_element.find_element(By.CSS_SELECTOR, '.discount, .offer, .promotion, [class*="discount"], [class*="aanbieding"]')
                product_data['discount'] = discount_elem.text.strip()
            except:
                product_data['discount'] = 'N/A'
            try:
                img_elem = product_element.find_element(By.CSS_SELECTOR, 'img')
                product_data['image_url'] = img_elem.get_attribute('src')
            except:
                product_data['image_url'] = 'N/A'
            try:
                link_elem = product_element.find_element(By.CSS_SELECTOR, 'a')
                product_data['product_url'] = link_elem.get_attribute('href')
            except:
                product_data['product_url'] = 'N/A'
            try:
                unit_elem = product_element.find_element(By.CSS_SELECTOR, '.product-unit, .unit, [class*="unit"]')
                product_data['unit'] = unit_elem.text.strip()
            except:
                product_data['unit'] = 'N/A'
                
            return product_data
            
        except Exception as e:
            print(f"Error extracting product info: {e}")
            return None
    
    def scrape(self, url, max_scrolls=50):
        """Main scraping function"""
        try:
            self.start_driver()
            print(f"Loading page: {url}")
            self.driver.get(url)
            
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.product-tile, .product-item, [class*="product"]')))
            try:
                cookie_button = self.driver.find_element(By.CSS_SELECTOR, '[class*="cookie"] button, #onetrust-accept-btn-handler')
                cookie_button.click()
                time.sleep(1)
            except:
                pass

            print("Starting to scroll and load products...")
            self.scroll_to_load_products(max_scrolls=max_scrolls)

            print("Extracting product information...")
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, '.product-tile, .product-item, [class*="product-tile"]')
            
            for idx, element in enumerate(product_elements, 1):
                product_info = self.extract_product_info(element)
                if product_info and product_info['name'] != 'N/A':
                    self.products.append(product_info)   
                if idx % 10 == 0:
                    print(f"Processed {idx}/{len(product_elements)} products...")
            
            print(f"Successfully scraped {len(self.products)} products")
            return self.products
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            return []
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def save_to_csv(self, filename='hoogvliet_offers.csv'):
        """Save scraped products to CSV"""
        if self.products:
            df = pd.DataFrame(self.products)
            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"Saved {len(self.products)} products to {filename}")
        else:
            print("No products to save")
    
    def save_to_json(self, filename='hoogvliet_offers.json'):
        """Save scraped products to JSON"""
        if self.products:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.products, f, ensure_ascii=False, indent=2)
            print(f"Saved {len(self.products)} products to {filename}")
        else:
            print("No products to save")

def main():
    scraper = HoogvlietScraper(headless=False)
    start_time = time.time()
    url = "https://www.hoogvliet.com/INTERSHOP/web/WFS/org-webshop-Site/nl_NL/-/EUR/ViewStandardCatalog-Browse?CategoryName=aanbiedingen&CatalogID=schappen"
    products = scraper.scrape(url, max_scrolls=200)
    
    if products:
        scraper.save_to_csv()
        scraper.save_to_json()
        
        print("\nSample of scraped products:")
        for product in products[:5]:
            print("-" * 50)
            print(f"Name: {product['name']}")
            print(f"Price: {product['price']}")
            print(f"Discount: {product['discount']}")
            print(f"Unit: {product['unit']}")
        
        print(f"\nTotal products scraped: {len(products)}")
        print("done in ", time.time() - start_time, "seconds")
    else:
        print("No products were scraped. Check the website structure or selectors.")

if __name__ == "__main__":
    main()