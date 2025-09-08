# Hoogvliet Promotions Scraper

This Python script is designed to scrape all current and upcoming promotional offers from the Hoogvliet supermarket website (`hoogvliet.com`). It operates by launching a headless browser to handle JavaScript-driven content, extracts the product information, normalizes it into a clean JSON format, and saves the results into separate files for current and upcoming offers.

### Features
-   **Concurrent Scraping:** Scrapes both the current and upcoming offer pages simultaneously to improve speed.
-   **Robust Pagination:** Reliably handles the "infinite scroll" mechanism on the category pages.
-   **Data Normalization:** Cleans and formats the scraped data.
-   **Separate Outputs:** Saves current and upcoming promotions into distinct JSON files (`current_offers.json`, `coming_offers.json`) inside an `output/` directory.

---

### Research & Approach Summary

*   **Approach:** A headless browser (Selenium) was chosen as the primary scraping tool. The Hoogvliet promotions page relies on JavaScript to dynamically load products as the user scrolls. A simple HTTP request would not be sufficient to get the full list of products, making a browser automation tool necessary.
*   **Source:** The data is scraped directly from the HTML of the promotions pages. No public API was identified during the initial investigation.
*   **Pagination:** The scraper handles two levels of "pagination":
    1.  **Timeframes:** It first identifies the URLs for both the "current" and "upcoming" promotional weeks.
    2.  **Infinite Scroll:** Within each timeframe page, it simulates a user scrolling to the bottom of the product list to trigger the JavaScript that loads more product tiles until all items are visible.
*   **Throttling:** A small, configurable delay (`wait_time` in `scroll_to_load_products`) is implemented between scroll actions.

---

### Setup and Execution

**Prerequisites:**
*   Python 3.9+
*   Google Chrome browser installed

**Instructions:**

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd hoogvliet
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    A `requirements.txt` file is included. Install the necessary libraries with pip:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Scraper:**
    Execute the script from your terminal:
    ```bash
    python scraper.py
    ```

---

### Configuration

Key settings can be adjusted in the `CONFIG` dictionary at the top of `scraper.py`:
*   `headless`: Set to `False` to watch the browser in action for debugging, or `True` for faster, background execution.
*   `concurrency`: Number of parallel browser instances to run. Defaults to 2 (one for current, one for coming offers).
*   `timeout`: The maximum time in seconds to wait for page elements to load.

---

### Output

The script will create an `output/` directory and save two files:
*   `output/current_offers.json`: Contains all products from the currently active promotional week.
*   `output/coming_offers.json`: Contains all products from the upcoming promotional week.

**Example JSON Record:**
```json
[
  {
    "id": "25992159",
    "title": "Bij 12,00 diverse soorten MM's, Maltesers, Snickers, Twix, Mars, Bounty gratis bezorging",
    "description": null,
    "promotion": "gratis bezorging bij 12,00",
    "price_now": null,
    "price_was": null,
    "image_url": "https://www.hoogvliet.com/INTERSHOP/static/WFS/org-webshop-Site/-/org/nl_NL/ACT/2025/36/230px172px/mars.jpg",
    "source_url": "http://www.hoogvliet.com/aanbiedingen/25992159;pgid=5VlWytn46atSRpS0VD87F2tT0000hO6I1I3x;sid=ZRz7Uq_SnyuJUsdv7nBUUbTYuEOc0kWieWwPBbDB5A83rg==",
    "start_date": "2025-09-10",
    "end_date": "2025-09-16",
    "child_products": []
  },
]