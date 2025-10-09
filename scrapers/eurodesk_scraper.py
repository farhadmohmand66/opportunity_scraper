import os
import re
import time
import json
import tkinter as tk
import undetected_chromedriver as uc
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

# ---------------------------
# Project paths
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"

# Config files
CATEGORY_KEYWORDS_FILE = CONFIG_DIR / "category_keywords.json"
COUNTRIES_FILE = CONFIG_DIR / "country.json"
CITIES_FILE = CONFIG_DIR / "world_cities.json"

# Output file
OUTPUT_FILE = DATA_DIR / "eurodesk_learning.json"

# Target URL
URL = "https://programmes.eurodesk.eu/learning"

# tweak waits if needed
SHORT_WAIT = 1
MEDIUM_WAIT = 2
LONG_WAIT = 3

def simple_init():
    driver = uc.Chrome(headless=False, use_subprocess=True)
    
    # Get screen dimensions dynamically
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.destroy()
    
    # Set window size and position
    driver.set_window_size(1200, screen_height - 200)
    driver.set_window_position(0, 0)  # Left side
    
    # Enforce zoom
    driver.execute_script("document.body.style.zoom='75%'")
    return driver

# ---------------------------
# Save JSON helper
# ---------------------------
def save_json(data, filepath):
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Data saved to {filepath}")
    except Exception as e:
        print(f"❌ Failed to save {filepath}: {e}")

# ---------------------------
# Load dictionaries
# ---------------------------
def load_json_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Could not load {filepath}: {e}")
        return {}

# ---------------------------
# Entity extraction (from user's code)
# ---------------------------
def load_countries_and_cities():
    try:
        countries_data = load_json_file(COUNTRIES_FILE)
        countries = [c.lower() for c in countries_data.get("countries", [])]

        cities_data = load_json_file(CITIES_FILE)
        cities = [c.lower() for c in cities_data.get("cities", [])]

        return countries, cities
    except Exception as e:
        print("Error loading countries/cities:", e)
        return [], []

def extract_categories_with_plurals(text_lower, category_keywords):
    matched_categories = []
    plural_mappings = {
        'y': 'ies', 's': 'es', 'x': 'es', 'ch': 'es', 'sh': 'es',
        'f': 'ves', 'fe': 'ves', 'o': 'es', 'us': 'i', 'is': 'es',
        'ix': 'ices', 'man': 'men', 'default': 's'
    }
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if re.search(r'\b' + re.escape(keyword_lower) + r'\b', text_lower):
                matched_categories.append(category)
                break
            # plural handling
            plural_added = False
            for ending, plural_ending in plural_mappings.items():
                if ending != 'default' and keyword_lower.endswith(ending):
                    plural_form = keyword_lower[:-len(ending)] + plural_ending
                    if re.search(r'\b' + re.escape(plural_form) + r'\b', text_lower):
                        matched_categories.append(category)
                        plural_added = True
                        break
                    plural_added = True
                    break
            if not plural_added:
                plural_form = keyword_lower + 's'
                if re.search(r'\b' + re.escape(plural_form) + r'\b', text_lower):
                    matched_categories.append(category)
                    break
    return matched_categories

def extract_countries(text_lower, countries):
    found = []
    for c in countries:
        if re.search(r'\b' + re.escape(c) + r'\b', text_lower):
            found.append(c.title())
    return found

def extract_cities(text_lower, cities):
    found = []
    for c in cities:
        if re.search(r'\b' + re.escape(c) + r'\b', text_lower):
            found.append(c.title())
    return found

def extract_entities_from_text(text, category_keywords, countries, cities):
    text_lower = (text or "").lower()
    return {
        "categories": extract_categories_with_plurals(text_lower, category_keywords),
        "countries": extract_countries(text_lower, countries),
        "cities": extract_cities(text_lower, cities),
    }

# ---------------------------
# Page-specific extractors
# ---------------------------
def extract_category_specific(driver):
    try:
        additional_info = driver.find_element(By.XPATH, '//div[@data-role="additional"]')
        category_text = additional_info.find_element(By.XPATH, './/span[1]').text.strip()
        parts = category_text.split(":")
        return parts[1].strip() if len(parts) > 1 else "N/A"
    except Exception:
        return "N/A"

def extract_date_specific(driver):
    try:
        # Try to find the date in the first specified element
        date_element = driver.find_element(By.XPATH, "//div[contains(@class, 'flex items-center gap-4')][2]/span")
        return date_element.text.strip()
    except Exception:
        print("First date element not found, trying the second one.")
        
        try:
            # Try to find the date in the second specified element
            date_element = driver.find_element(By.XPATH, "//div[contains(@class, 'flex items-center gap-4')]/span[@class='text-lg font-bold uppercase']")
            return date_element.text.strip()
        except Exception:
            return "No date found"

def extract_url_specific(driver):
    xpaths = [
        "//p[contains(text(), 'Check')]/a",
        "//p[strong[contains(text(), 'Read more')]]/a",
        "//p[strong[contains(text(), 'Find out more')]]/a",
        "//a[contains(text(), 'Find out more')]"
    ]
    for xp in xpaths:
        try:
            el = driver.find_element(By.XPATH, xp)
            href = el.get_attribute("href")
            if href:
                return href
        except Exception:
            continue
    return "No URL found"

def extract_description_specific(driver):
    try:
        description_parts = []
        body_elements = driver.find_elements(By.XPATH, '//div[@data-role="body"]')
        if not body_elements:
            return "No description found"
        for body in body_elements:
            # preserve order of child elements
            child_elems = body.find_elements(By.XPATH, "./*")
            for child in child_elems:
                tag = child.tag_name.lower()
                text = child.text.strip()
                if not text:
                    continue
                if tag == "p":
                    if text not in description_parts:
                        description_parts.append(text)
                elif tag in ("ul", "ol"):
                    items = child.find_elements(By.TAG_NAME, "li")
                    for li in items:
                        li_text = li.text.strip()
                        if li_text:
                            description_parts.append(f"• {li_text}")
        return "\n".join(description_parts) if description_parts else "No description found"
    except Exception as e:
        print("Error extracting description:", e)
        return "No description found"

def extract_banner_image(driver):
    """Extract banner image URL from the hero section"""
    try:
        # Look for the hero section with the banner image
        hero_section = driver.find_element(By.CSS_SELECTOR, '[data-role="hero"]')
        image_element = hero_section.find_element(By.TAG_NAME, 'img')
        image_url = image_element.get_attribute('src')
        return image_url
    except Exception as e:
        print(f"⚠️ Could not extract banner image: {e}")
        return "No image found"

def close_popup(driver):
    try:
        wait = WebDriverWait(driver, 3)
        close_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "img[alt='Close'][onclick*='closeProgram']")))
        driver.execute_script("arguments[0].click();", close_btn)
        time.sleep(SHORT_WAIT)
    except Exception:
        try:
            from selenium.webdriver.common.keys import Keys
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(SHORT_WAIT)
        except Exception:
            pass

def scrape_popup_data(driver, card_number, mode_of_work, category_keywords, countries, cities):
    """Scrape a single popup and return structured dict including modeOfWork."""
    time.sleep(LONG_WAIT)  # allow popup to load
    data = {}
    try:
        # title
        try:
            data['title'] = driver.find_element(By.CSS_SELECTOR, "[data-role='title'] .text-2xl").text.strip()
        except Exception:
            data['title'] = "No title found"

        data['date'] = extract_date_specific(driver)
        
        if data['date'].upper() == "UPCOMING":
            print(f"  ⏭️  Skipping card {card_number} - UPCOMING opportunity")
            return None
        
        data['url'] = extract_url_specific(driver)
        data['description'] = extract_description_specific(driver)
        data['typeOfOpportunity'] = extract_category_specific(driver)
        data['bannerImage'] = extract_banner_image(driver)

        # extract entities from description
        desc = data.get('description', "")
        if desc and desc != "No description found":
            entities = extract_entities_from_text(desc, category_keywords, countries, cities)
            data['categories'] = entities['categories']
            data['countries'] = entities['countries']
            data['cities'] = entities['cities']
        else:
            data['categories'] = []
            data['countries'] = []
            data['cities'] = []

        data['card_number'] = card_number
        data['modeOfWork'] = mode_of_work
    except Exception as e:
        data = {"error": str(e), "card_number": card_number, "modeOfWork": mode_of_work}
    return data

# ---------------------------
# Workflow helpers (filtering + results)
# ---------------------------
def ensure_young_people_checked(driver):
    try:
        wait = WebDriverWait(driver, 12)
        checkbox_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='targets[Young People]']")))
        driver.execute_script("arguments[0].click();", checkbox_input)
        print("✅ Young people selected")
        time.sleep(SHORT_WAIT)
    except Exception as e:
        print("Failed to check 'Young People' checkbox:", e)

def click_more_filters(driver):
    try:
        wait = WebDriverWait(driver, 10)
        more_filters = wait.until(EC.element_to_be_clickable((By.XPATH, "//summary[contains(., 'More filters')]")))
        driver.execute_script("arguments[0].scrollIntoView(true);", more_filters)
        driver.execute_script("arguments[0].click();", more_filters)
        time.sleep(SHORT_WAIT)
    except Exception as e:
        print("Failed to click 'More filters':", e)

def set_country(driver, country_name):
    try:
        wait = WebDriverWait(driver, 10)
        country_select = wait.until(EC.presence_of_element_located((By.NAME, "eligible-country")))
        select = Select(country_select)
        select.select_by_visible_text(country_name)
        time.sleep(SHORT_WAIT)
    except Exception as e:
        print(f"Failed to select country {country_name}:", e)

def reset_mode_filters(driver):
    """Reset both Online and Onsite filters to unchecked state"""
    online_css = "input[name='format[online]']"
    onsite_css = "input[name='format[onsite]']"
    try:
        wait = WebDriverWait(driver, 10)
        online_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, online_css)))
        onsite_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, onsite_css)))

        # Uncheck both if they are checked
        if online_box.is_selected():
            driver.execute_script("arguments[0].click();", online_box)
            time.sleep(SHORT_WAIT)

        if onsite_box.is_selected():
            driver.execute_script("arguments[0].click();", onsite_box)
            time.sleep(SHORT_WAIT)

        print("✅ Mode filters reset (both unchecked)")
    except Exception as e:
        print("Error resetting mode filters:", e)

def set_mode_filter(driver, mode: str):
    wait_for_page_ready(driver)
    check_and_wait_for_captcha(driver)
    """
    mode: "Online" or "Onsite"
    First resets both filters, then sets the desired one.
    """
    # First reset both filters
    reset_mode_filters(driver)
    
    online_css = "input[name='format[online]']"
    onsite_css = "input[name='format[onsite]']"
    
    try:
        wait = WebDriverWait(driver, 10)
        
        if mode.lower() == "online":
            online_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, online_css)))
            if not online_box.is_selected():
                driver.execute_script("arguments[0].click();", online_box)
                print(f"✅ Online filter selected")
                
        elif mode.lower() == "onsite":
            onsite_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, onsite_css)))
            if not onsite_box.is_selected():
                driver.execute_script("arguments[0].click();", onsite_box)
                print(f"✅ Onsite filter selected")
        
        time.sleep(SHORT_WAIT)
        
    except Exception as e:
        print(f"Error setting {mode} filter:", e)

def click_see_results(driver):
    try:
        wait = WebDriverWait(driver, 10)
        see_results_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'See results')]")))
        driver.execute_script("arguments[0].click();", see_results_btn)
        time.sleep(SHORT_WAIT)
    except Exception as e:
        print("Failed to click See results:", e)

def wait_for_results_to_load(driver, timeout=15):
    """
    Wait until at least one card is present or timeout.
    Return number of cards found.
    """
    try:
        wait = WebDriverWait(driver, timeout)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-role='card']")))
    except Exception:
        pass
    # brief pause then count
    time.sleep(2)
    cards = driver.find_elements(By.CSS_SELECTOR, "[data-role='card']")
    return len(cards)

# ---------------------------
# Core scraping per-mode
# ---------------------------
def process_all_cards_for_mode(driver, category_keywords, mode_of_work):
    """
    Process cards in order and stop at the first UPCOMING post,
    since UPCOMING posts appear after open opportunities.
    """
    scraped_data = []
    countries, cities = load_countries_and_cities()

    # gather fresh list of cards
    cards = driver.find_elements(By.CSS_SELECTOR, "[data-role='card']")
    print(f"[{mode_of_work}] Found {len(cards)} cards to process")

    for i in range(len(cards)):
        print(f"\n🔄 [{mode_of_work}] Processing card {i+1}/{len(cards)}...")
        
        try:
            # re-find cards each iteration - page may re-render
            current_cards = driver.find_elements(By.CSS_SELECTOR, "[data-role='card']")
            if i >= len(current_cards):
                break
            card = current_cards[i]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
            time.sleep(SHORT_WAIT)
            driver.execute_script("arguments[0].click();", card)
            time.sleep(LONG_WAIT)

            item = scrape_popup_data(driver, card_number=i + 1, mode_of_work=mode_of_work,
                                    category_keywords=category_keywords,
                                    countries=countries, cities=cities)
            
            if item is not None:
                # ✅ Successfully scraped a valid post (not UPCOMING)
                scraped_data.append(item)
                print(f"  ✅ Successfully scraped card {i+1}")
            else:
                # ✅ First UPCOMING post detected - STOP PROCESSING
                print(f"  🛑 First UPCOMING post detected at card {i+1}. Stopping processing.")
                print(f"  💡 Reason: UPCOMING posts appear after open opportunities, so all remaining posts are UPCOMING.")
                close_popup(driver)
                break

            close_popup(driver)
            time.sleep(SHORT_WAIT)
            
        except Exception as e:
            print(f"❌ Error processing card {i+1} [{mode_of_work}]: {e}")
            try:
                close_popup(driver)
            except Exception:
                pass
            # Continue to next card even if there's an error
            continue

    print(f"\n✅ [{mode_of_work}] Completed scraping {len(scraped_data)} items (stopped at card {i+1})")
    return scraped_data

# ---------------------------
# Dedup & Save
# ---------------------------
def dedupe_combined(items):
    seen = set()
    unique = []
    duplicates = []
    
    for it in items:
        key = None
        url = it.get("url", "")
        title = it.get("title", "")
        date = it.get("date", "")
        
        if url and url != "No URL found":
            key = url
        else:
            key = f"{title}||{date}"
            
        if key not in seen:
            seen.add(key)
            unique.append(it)
        else:
            duplicates.append({"key": key, "title": title, "date": date})
    
    if duplicates:
        print(f"🔍 Found {len(duplicates)} duplicate(s):")
        for dup in duplicates:
            print(f"   - {dup['title']} | {dup['date']}")
    
    return unique
# ------------------------
# captch solver
# -----------------------------
def check_and_wait_for_captcha(driver, timeout=30):
    """Check if CAPTCHA is present and wait for manual solving"""
    try:
        # Common CAPTCHA indicators
        captcha_indicators = [
            "iframe[src*='captcha']",
            "div[class*='captcha']",
            "iframe[src*='recaptcha']",
            "div[class*='recaptcha']",
            "iframe[src*='challenge']"
        ]
        
        for indicator in captcha_indicators:
            if driver.find_elements(By.CSS_SELECTOR, indicator):
                print("🛡️ CAPTCHA detected. Please solve it manually...")
                WebDriverWait(driver, timeout).until(
                    lambda d: not d.find_elements(By.CSS_SELECTOR, indicator)
                )
                print("✅ CAPTCHA solved, continuing...")
                time.sleep(2)
                return True
    except Exception:
        pass
    return False

def wait_for_page_ready(driver, timeout=10):
    """Wait for page to be fully loaded and ready"""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(2)  # Additional safety wait
    except Exception as e:
        print(f"⚠️ Page not fully ready: {e}")

# ---------------------------
# Main workflow - CORRECTED
# ---------------------------
def main():
    driver = simple_init()
    
    try:
        print(f"🌐 Navigating to {URL}")
        driver.get(URL)

#-----------------------------------------------------

        print("⏳ Waiting for initial page load...")
        print("⏳ Waiting for you to solve CAPTCHA (if shown)...")
        WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Check for CAPTCHA immediately
        check_and_wait_for_captcha(driver)

        # Then wait for cards with shorter timeout
        try:
            WebDriverWait(driver, 50).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-role='card']"))
            )
        except:
            print("⚠️ Cards not immediately available, checking for CAPTCHA...")
            check_and_wait_for_captcha(driver)
            # Retry waiting for cards
            WebDriverWait(driver, 50).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-role='card']"))
            )

#-----------------------------------------------
        try:
            driver.execute_script("document.body.style.zoom='75%'")
        except:
            pass
        print("✅ Website fully loaded")

        # Set base filters once
        ensure_young_people_checked(driver)
        click_more_filters(driver)
        set_country(driver, "Bulgaria")

        # Load category keywords
        category_keywords = load_json_file(CATEGORY_KEYWORDS_FILE) or {}
        if not category_keywords:
            print("⚠️ Warning: category_keywords is empty or missing")

        all_results = []

        # Process Online first
        print("\n" + "="*50)
        print("🚀 Starting run for mode: Online")
        print("="*50)

        set_mode_filter(driver, "Online")
        click_see_results(driver)
        time.sleep(5)

        count = wait_for_results_to_load(driver, timeout=12)
        print(f"📊 [Online] Cards after filtering: {count}")

        online_results = process_all_cards_for_mode(driver, category_keywords, "Online")
        all_results.extend(online_results)

        print(f"✅ Online scraping complete: {len(online_results)} items")

        # Reset and process Onsite
        print("\n" + "="*50)
        print("🔄 Switching to mode: Onsite")
        print("="*50)

        # Reset filters and set Onsite
        set_mode_filter(driver, "Onsite")
        click_see_results(driver)
        time.sleep(5)

        count = wait_for_results_to_load(driver, timeout=12)
        print(f"📊 [Onsite] Cards after filtering: {count}")

        onsite_results = process_all_cards_for_mode(driver, category_keywords, "Onsite")
        all_results.extend(onsite_results)

        print(f"✅ Onsite scraping complete: {len(onsite_results)} items")

        # Final processing
        combined = dedupe_combined(all_results)
        save_json(combined, OUTPUT_FILE)

        # Print summary
        print("\n" + "="*60)
        print("📊 FINAL SUMMARY")
        print("="*60)
        print(f"📦 Online items: {len(online_results)}")
        print(f"📦 Onsite items: {len(onsite_results)}")
        print(f"📦 Total items collected (raw): {len(all_results)}")
        print(f"✨ Total items after dedupe: {len(combined)}")
        
        # Count skipped UPCOMING cards
        total_cards_processed = sum(1 for item in all_results if item.get('date') != 'UPCOMING')
        print(f"⏭️  UPCOMING opportunities skipped: {len(all_results) - total_cards_processed}")
        
        if combined:
            print("\n📄 Sample item:")
            print(json.dumps(combined[0], indent=2, ensure_ascii=False))

    finally:
        print("\n🔚 Closing driver")
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    main()