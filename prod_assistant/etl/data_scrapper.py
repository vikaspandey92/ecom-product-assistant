import time
import csv
import logging
from typing import List
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)

class FlipkartScraper:

    def __init__(self):
        pass

    # --------------------------------------------------
    # DRIVER SETUP (Stable + Headless + Anti-Detection)
    # --------------------------------------------------
    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/144.0.0.0 Safari/537.36"
        )

        service = Service()  # assumes chromedriver in PATH
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)

        return driver

    # --------------------------------------------------
    # CLOSE LOGIN POPUP IF PRESENT
    # --------------------------------------------------
    def _close_login_popup(self, driver):
        try:
            close_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'✕')]"))
            )
            close_btn.click()
            logging.info("Closed login popup")
        except:
            pass

    # --------------------------------------------------
    # MAIN SCRAPER FUNCTION
    # --------------------------------------------------
    def scrape_flipkart_products(
        self,
        query: str,
        max_products: int = 1,
        review_count: int = 2
    ) -> List[List[str]]:

        logging.info(f"🔍 Starting scrape for: {query}")
        driver = self._init_driver()
        results = []

        try:
            search_url = f"https://www.flipkart.com/search?q={query}"
            driver.get(search_url)

            self._close_login_popup(driver)

            # Wait for product cards
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "_1AtVbE"))
                )
            except TimeoutException:
                logging.warning("No products loaded.")
                return []

            product_links = driver.find_elements(By.XPATH, "//a[contains(@href,'/p/')]")
            product_links = product_links[:max_products]

            logging.info(f"Found {len(product_links)} products")

            for index, product in enumerate(product_links):

                try:
                    link = product.get_attribute("href")
                    driver.execute_script("window.open(arguments[0]);", link)
                    driver.switch_to.window(driver.window_handles[1])

                    time.sleep(2)

                    # -------------------------
                    # PRODUCT TITLE
                    # -------------------------
                    try:
                        title = driver.find_element(By.CLASS_NAME, "B_NuCI").text
                    except:
                        title = "N/A"

                    # -------------------------
                    # RATING
                    # -------------------------
                    try:
                        rating = driver.find_element(By.CLASS_NAME, "_3LWZlK").text
                    except:
                        rating = "N/A"

                    # -------------------------
                    # TOTAL REVIEWS
                    # -------------------------
                    try:
                        total_reviews = driver.find_element(
                            By.XPATH,
                            "//span[contains(text(),'Ratings')]"
                        ).text
                    except:
                        total_reviews = "N/A"

                    # -------------------------
                    # TOP REVIEWS
                    # -------------------------
                    reviews = []
                    review_elements = driver.find_elements(By.CLASS_NAME, "_6K-7Co")

                    for r in review_elements[:review_count]:
                        reviews.append(r.text)

                    if not reviews:
                        reviews.append("N/A")

                    results.append([
                        query,
                        title,
                        rating,
                        total_reviews,
                        " | ".join(reviews)
                    ])

                    logging.info(f"Scraped product {index+1}")

                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

                except Exception as e:
                    logging.error(f"Error scraping product: {e}")
                    continue

        except WebDriverException as e:
            logging.error(f"WebDriver Error: {e}")

        finally:
            driver.quit()
            logging.info("Driver closed")

        return results


    # --------------------------------------------------
    # SAVE CSV
    # --------------------------------------------------
    def save_to_csv(self, data, filename="product_reviews.csv"):
        if os.path.isabs(filename):
            path = filename
        elif os.path.dirname(filename):
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            path = filename
        else:
            path = os.path.join(self.output_dir, filename)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "product_id",
                "product_title",
                "rating",
                "total_reviews",
                "price",
                "top_reviews"
            ])
            writer.writerows(data)

        print(f"\nSaved to {path}")


# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------
if __name__ == "__main__":
    scraper = FlipkartScraper()

    query = input("Enter product to search: ")

    products = scraper.scrape_flipkart_products(
        query=query,
        max_products=3,
        review_count=2
    )

    scraper.save_to_csv(products)
