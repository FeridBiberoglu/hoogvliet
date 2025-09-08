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