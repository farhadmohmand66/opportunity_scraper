import json
import re
import time
import os
import tkinter as tk
import undetected_chromedriver as uc
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from datetime import datetime


class EuropeanYouthPortalScraper:

    def __init__(self, max_load_more=0):
        self.driver = None
        self.max_load_more = max_load_more
        self.all_opportunities = []

        # Resolve project root reliably (fallback to cwd if __file__ isn't available)
        try:
            current_file = Path(__file__).resolve()
            scrapers_dir = current_file.parent
            project_root = scrapers_dir.parent
        except Exception:
            project_root = Path.cwd()

        # Set folder paths
        self.data_folder = project_root / "data"
        self.config_dir = project_root / "config"

        print(f"📁 Project root: {project_root}")
        print(f"📁 Data folder: {self.data_folder}")
        print(f"📁 Config folder: {self.config_dir}")

    def setup_driver(self):
        """Initialize undetected-chrome driver with dynamic screen dimensions and enforced zoom."""
        try:
            self.driver = uc.Chrome(headless=False, use_subprocess=True)

            # Get screen dimensions dynamically
            try:
                root = tk.Tk()
                screen_width = root.winfo_screenwidth()
                screen_height = root.winfo_screenheight()
                root.destroy()
            except Exception:
                screen_width, screen_height = 1200, 800

            # Set window size and position
            self.driver.set_window_size(1200, max(screen_height - 200, 600))
            self.driver.set_window_position(0, 0)  # Left side

            # Enforce zoom (best-effort)
            try:
                self.driver.execute_script("document.body.style.zoom='75%'")
            except Exception:
                pass

            print("✅ Driver setup completed")
            return True
        except Exception as e:
            print(f"❌ Error setting up driver: {e}")
            return False

    def click_load_more_safe(self, max_clicks=0):
        """Click Load More button safely with multiple fallback locators."""
        clicks_done = 0

        while clicks_done < max_clicks:
            try:
                # Try multiple locator strategies (some pages use different text/classes)
                btn = None
                try:
                    btn = WebDriverWait(self.driver, 6).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]") )
                    )
                except Exception:
                    # fallback: any button with load-more class or data attribute
                    try:
                        btn = WebDriverWait(self.driver, 6).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.load-more, button[data-action='load-more'], a.load-more"))
                        )
                    except Exception:
                        btn = None

                if not btn:
                    print("✅ No more Load More button found (or timed out)")
                    break

                self.driver.execute_script("arguments[0].scrollIntoView();", btn)
                time.sleep(0.8)
                try:
                    btn.click()
                except Exception:
                    # last resort
                    self.driver.execute_script("arguments[0].click();", btn)

                clicks_done += 1
                print(f"✅ Load More clicked ({clicks_done}/{max_clicks})")

                # Wait for new cards to appear (or a short pause)
                WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".card-item"))
                )
                time.sleep(1.5)

            except TimeoutException:
                print("✅ Load more timed out")
                break
            except Exception as e:
                print(f"❌ Error clicking Load More: {e}")
                break

        return clicks_done

    def extract_all_opportunity_urls(self):
        """Extract all opportunity URLs from the page"""
        urls = []
        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR, ".card-item")
            print(f"🔍 Found {len(cards)} card items")

            for card in cards:
                try:
                    read_more_link = card.find_element(By.CSS_SELECTOR, "a.btn[href*='/solidarity/opportunity/']")
                    href = read_more_link.get_attribute('href')
                    if href and href not in urls:
                        if href.startswith('/'):
                            href = "https://youth.europa.eu" + href
                        urls.append(href)
                        print(f"✅ Found: {href}")
                except NoSuchElementException:
                    # try alternative link inside card
                    try:
                        link = card.find_element(By.TAG_NAME, 'a')
                        href = link.get_attribute('href')
                        if href and '/solidarity/opportunity/' in href and href not in urls:
                            urls.append(href)
                            print(f"✅ Found (alt): {href}")
                    except Exception:
                        continue

            return urls
        except Exception as e:
            print(f"❌ Error extracting URLs: {e}")
            return []

    def check_bulgaria_eligible(self):
        """Robust check if Bulgaria is eligible for the opportunity"""
        try:
            # Try a few different XPaths commonly used on the site
            candidates = []

            xpaths = [
                "//h6[contains(., 'Looking for participants from')]/following-sibling::p[1]",
                "//h6[contains(., 'Looking for participants')]/following-sibling::p[1]",
                "//p[contains(., 'Looking for participants from')]",
                "//p[contains(., 'Participants from')]",
            ]

            for xp in xpaths:
                try:
                    elems = self.driver.find_elements(By.XPATH, xp)
                    for e in elems:
                        txt = e.text.strip()
                        if txt:
                            candidates.append(txt)
                except Exception:
                    continue

            # Fallback: search the whole page for phrases
            if not candidates:
                page_text = self.driver.find_element(By.TAG_NAME, 'body').text
                for line in page_text.split('\n'):
                    low = line.strip().lower()
                    if 'looking for participants' in low or 'participants from' in low:
                        candidates.append(line.strip())

            if not candidates:
                print("❌ No participants section found")
                return False

            countries_text = ' '.join(candidates).lower()
            print(f"🔍 Countries (raw): {countries_text[:200]}{'...' if len(countries_text)>200 else ''}")

            # Simple checks
            if 'bulgaria' in countries_text:
                return True

            global_terms = [
                'all countries', 'all nationalities', 'worldwide', 'global',
                'europe', 'european', 'eu countries', 'european union',
                'any country', 'any nationality', 'erasmus', 'erasmus+', 'erasmus plus', 'youth programme countries',
                'eu residents'
            ]
            if any(term in countries_text for term in global_terms):
                return True

            return False

        except NoSuchElementException:
            print("❌ No participants section (NoSuchElementException)")
            return False
        except Exception as e:
            print(f"⚠️ Error while checking eligibility: {e}")
            return False

    def extract_title(self):
        """Extract opportunity title"""
        try:
            title_element = self.driver.find_element(By.CSS_SELECTOR, ".opportunity-detail h1")
            return title_element.text.strip()
        except Exception:
            try:
                # fallback
                title_element = self.driver.find_element(By.TAG_NAME, 'h1')
                return title_element.text.strip()
            except Exception:
                return None

    def extract_deadline(self):
        """Extract application deadline with some basic parsing"""
        try:
            raw = self.driver.find_element(By.XPATH, "//h6[contains(., 'Deadline')]/following-sibling::p[1]").text
            raw = raw.strip()

            # Try to extract common date formats
            m = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", raw)
            if m:
                return m.group(1)
            m2 = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
            if m2:
                return m2.group(1)

            # If the text contains a colon, often the date follows
            if ':' in raw:
                parts = raw.split(':', 1)
                return parts[1].strip()

            return raw
        except Exception:
            return None

    def extract_banner_image(self):
        """Extract banner image URL - return None if not found (no long stacktraces)."""
        try:
            imgs = self.driver.find_elements(By.CSS_SELECTOR, 'img.org-logo.responsive-img')
            if imgs:
                return imgs[0].get_attribute('src')

            # fallback: first image inside opportunity detail
            imgs = self.driver.find_elements(By.CSS_SELECTOR, '.opportunity-detail img')
            if imgs:
                return imgs[0].get_attribute('src')

            return None
        except Exception:
            return None

    def extract_categories(self):
        """Extract activity topics/categories"""
        try:
            topics_header = self.driver.find_element(By.XPATH, "//h6[contains(text(), 'Activity topics')]")
            topic_elements = topics_header.find_elements(By.XPATH, "./following-sibling::p[position() <= 4]")

            categories = []
            for topic_element in topic_elements:
                topic_text = topic_element.text.strip()
                if topic_text:
                    categories.append(topic_text)
            return categories
        except Exception:
            return []

    def extract_location(self):
        """Extract city and country more robustly"""
        try:
            location_header = self.driver.find_element(By.XPATH, "//h6[contains(text(), 'Activity location')]")
            location_element = location_header.find_element(By.XPATH, "./following-sibling::p[1]")
            location_text = location_element.text.strip()

            parts = [p.strip() for p in location_text.split(',') if p.strip()]
            if len(parts) == 0:
                return None, None
            country = parts[-1]
            city = ', '.join(parts[:-1]) if len(parts) > 1 else None
            return city, country
        except Exception:
            return None, None

    def extract_description(self):
        """Extract opportunity description robustly (fix: use first card-content)"""
        try:
            card_contents = self.driver.find_elements(By.CSS_SELECTOR, "div.card.od-card div.card-content")
            if card_contents and len(card_contents) > 0:
                # Use the first card-content (index 0) — previous code used index 1 and missed descriptions.
                desc = card_contents[0].text.strip()
                return desc if desc else None

            # fallback: try common selectors for description
            try:
                desc_el = self.driver.find_element(By.CSS_SELECTOR, '.opportunity-detail .description, .opportunity-detail .card-content')
                return desc_el.text.strip()
            except Exception:
                return None

        except Exception as e:
            print(f"⚠️ Error extracting description: {e}")
            return None

    def extract_opportunity_type(self, post_title, description):
        """Extract type of opportunity"""
        text = f"{post_title or ''} {description or ''}".lower()

        type_keywords = {
            'competition': ['competition', 'contest', 'prize', 'award', 'challenge', 'tournament'],
            'exchange': ['exchange', 'cultural exchange', 'youth exchange', 'student exchange'],
            'event': ['event', 'conference', 'summit', 'workshop', 'seminar', 'forum', 'meeting'],
            'scholarship': ['scholarship', 'grant', 'funding', 'financial aid', 'stipend'],
            'erasmus': ['erasmus', 'erasmus+', 'erasmus plus'],
            'volunteering': ['volunteering', 'volunteer', 'solidarity']
        }

        for opp_type, keywords in type_keywords.items():
            if any(keyword in text for keyword in keywords):
                return opp_type

        return 'volunteering'

    def extract_mode_of_work(self, description):
        """Extract mode of work"""
        if not description:
            return 'on-site'

        text = description.lower()

        remote_terms = ['remote', 'virtual', 'digital', 'zoom', 'webinar', 'from home']
        onsite_terms = ['on-site', 'onsite', 'in-person', 'physical', 'venue', 'location', 'face-to-face']
        hybrid_terms = ['hybrid', 'both online and in-person', 'online and onsite', 'partially remote']

        if any(term in text for term in hybrid_terms):
            return 'hybrid'
        elif any(term in text for term in remote_terms):
            return 'remote'
        elif any(term in text for term in onsite_terms):
            return 'on-site'

        return 'on-site'

    def scrape_single_opportunity(self, url, opportunity_number):
        """Scrape data from a single opportunity URL"""
        try:
            print(f"\n{'='*50}")
            print(f"📝 Processing Opportunity {opportunity_number}")
            print(f"{'='*50}")
            print(f"🔗 Navigating to: {url}")

            # Navigate to opportunity
            self.driver.get(url)

            # Wait a short while for the main content to appear
            try:
                WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.opportunity-detail, h1'))
                )
            except Exception:
                # continue anyway; we'll handle missing elements
                pass

            time.sleep(1)

            # Check Bulgaria eligibility first
            is_eligible = self.check_bulgaria_eligible()
            print(f"🇧🇬 Bulgaria eligible: {is_eligible}")

            # Only proceed if Bulgaria is eligible
            if not is_eligible:
                print("🚫 Skipping - Bulgaria not eligible")
                return None

            # Extract all data
            title = self.extract_title()
            deadline = self.extract_deadline()
            categories = self.extract_categories()
            city, country = self.extract_location()
            description = self.extract_description()
            banner_image = self.extract_banner_image()

            opportunity_type = self.extract_opportunity_type(title, description)
            mode_of_work = self.extract_mode_of_work(description)

            print(f"🎯 Type: {opportunity_type}")
            print(f"💼 Mode: {mode_of_work}")

            opportunity_data = {
                "postNo": opportunity_number,
                "title": title,
                "city": city,
                "country": country,
                "description": description,
                "validUntil": deadline,
                "type": opportunity_type,
                "modeOfWork": mode_of_work,
                "categories": categories,
                "applicationUrl": url,
                "bannerImage": banner_image,
                "bulgariaEligible": is_eligible
            }

            print(f"✅ Successfully processed Opportunity {opportunity_number}")
            return opportunity_data

        except Exception as e:
            print(f"❌ Error processing Opportunity {opportunity_number}: {e}")
            return None

    def save_to_json(self, filename="european_youth_portal_bulgaria_eligible.json"):
        """Save data to JSON file in data folder"""
        try:
            # Create data folder if it doesn't exist
            os.makedirs(self.data_folder, exist_ok=True)

            # Create full file path
            file_path = os.path.join(self.data_folder, filename)

            # Save the data
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.all_opportunities, f, indent=2, ensure_ascii=False)

            print(f"💾 Data saved to: {file_path}")
            print(f"📊 Total Bulgaria-eligible opportunities saved: {len(self.all_opportunities)}")

        except Exception as e:
            print(f"❌ Error saving to JSON: {e}")

    def run(self):
        """Main function to run the scraper"""
        try:
            # Setup driver
            if not self.setup_driver():
                return

            # Navigate to main page
            URL = "https://youth.europa.eu/go-abroad/volunteering/opportunities_en"
            print(f"🌐 Navigating to {URL}")
            self.driver.get(URL)
            time.sleep(4)
            try:
                self.driver.execute_script("document.body.style.zoom='75%'")
            except:
                pass

            # Click Load More buttons
            if self.max_load_more > 0:
                clicks = self.click_load_more_safe(self.max_load_more)
                print(f"🎯 Total Load More clicks: {clicks}")

            # Extract all opportunity URLs
            opportunity_urls = self.extract_all_opportunity_urls()
            print(f"📊 Total opportunity URLs found: {len(opportunity_urls)}")

            if not opportunity_urls:
                print("❌ No opportunities found")
                return

            # Process each opportunity
            successful_opportunities = 0
            for i, url in enumerate(opportunity_urls, 1):
                opportunity_data = self.scrape_single_opportunity(url, i)
                if opportunity_data:
                    self.all_opportunities.append(opportunity_data)
                    successful_opportunities += 1

                # Add delay between requests
                time.sleep(1.5)

            # Save only Bulgaria-eligible data
            self.save_to_json()

            print(f"\n{'='*50}")
            print(f"🎉 SCRAPING COMPLETED!")
            print(f"📊 Total opportunities processed: {len(opportunity_urls)}")
            print(f"🇧🇬 Bulgaria-eligible opportunities found: {successful_opportunities}")
            print(f"💾 Data saved to: {os.path.join(self.data_folder, 'european_youth_portal_bulgaria_eligible.json')}")
            print(f"{'='*50}")

        except Exception as e:
            print(f"❌ Error in main execution: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                print("🔚 Driver closed")


# Run the scraper
if __name__ == "__main__":
    scraper = EuropeanYouthPortalScraper(max_load_more=0)  # Set max_load_more as needed
    scraper.run()
