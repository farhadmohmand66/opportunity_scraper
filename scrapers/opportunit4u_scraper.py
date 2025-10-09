import json
import re
import time
import os
import tkinter as tk
import sys
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from datetime import datetime

# Add project root to path to import config files
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up one level from scrapers/
config_dir = os.path.join(project_root, "config")
data_dir = os.path.join(project_root, "data")

class Opportunit4uScraper:
    def __init__(self, max_load_more):
        self.driver = None
        self.max_load_more = max_load_more
        self.all_opportunities = []
        self.bulgaria_eligible_count = 0
        
        # Set paths based on project structure
        self.project_root = project_root
        self.data_folder = data_dir
        self.config_dir = config_dir
        
        # Configuration file paths
        self.categories_path = os.path.join(self.config_dir, "category_keywords.json")
        self.countries_path = os.path.join(self.config_dir, "country.json")
        self.cities_path = os.path.join(self.config_dir, "world_cities.json")

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
    
    def load_all_posts(self):
        """Load all posts by clicking Load More button multiple times"""
        try:
            URL = "https://www.opportunit4u.com/"
            print(f"🌐 Navigating to {URL}")
            self.driver.get(URL)
            time.sleep(5)
            
            load_count = 0
            while load_count < self.max_load_more:
                try:
                    load_more_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.blog-pager-older-link.load-more"))
                    )
                    
                    # Scroll to the button
                    self.driver.execute_script("arguments[0].scrollIntoView();", load_more_btn)
                    time.sleep(1)
                    
                    # Click using JavaScript
                    self.driver.execute_script("arguments[0].click();", load_more_btn)
                    
                    load_count += 1
                    print(f"✅ Load More clicked ({load_count}/{self.max_load_more})")
                    time.sleep(3)
                    
                except (TimeoutException, NoSuchElementException):
                    print("✅ No more Load More buttons found")
                    break
                except Exception as e:
                    print(f"⚠️ Error clicking Load More: {e}")
                    break
            
            # Get all post URLs instead of elements to avoid stale references
            post_urls = self.extract_all_post_urls()
            print(f"📊 Total post URLs found: {len(post_urls)}")
            return post_urls
            
        except Exception as e:
            print(f"❌ Error loading posts: {e}")
            return []
    
    def extract_all_post_urls(self):
        """Extract all post URLs from the current page"""
        urls = []
        try:
            posts = self.driver.find_elements(By.CSS_SELECTOR, ".blog-post.hentry.index-post")
            for post in posts:
                try:
                    title_link = post.find_element(By.CSS_SELECTOR, "h2.post-title a")
                    href = title_link.get_attribute('href')
                    if href and href not in urls:
                        urls.append(href)
                except NoSuchElementException:
                    continue
        except Exception as e:
            print(f"Error extracting post URLs: {e}")
        return urls
    
    def extract_opportunity_link(self):
        """Extract application link from post"""
        target_texts = ["Apply Now", "application form", "Opportunity Website"]
        
        for text in target_texts:
            try:
                if text == "Apply Now":
                    link = self.driver.find_element(By.XPATH, f"//a[.//b[contains(text(), '{text}')]]")
                else:
                    link = self.driver.find_element(By.XPATH, f"//a[b[contains(text(), '{text}')]]")
                return link.get_attribute("href")
            except:
                continue
        return None
    
    def get_deadline_date(self):
        """Extract and convert deadline date to standard format"""
        try:
            deadline_text = WebDriverWait(self.driver, 1).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'application deadline:')]"))
            ).text

            deadline_line = [line.strip() for line in deadline_text.split("\n") 
                            if "application deadline:" in line.lower()][0]

            deadline_date = deadline_line.split("Application deadline:")[1].split("(")[0].strip()
            return deadline_date

        except Exception as e:
            # print(f"⚠️ Error extracting deadline: {e}")
            return None
    
    def extract_description(self):
        """Extract post description"""
        selectors = [
            ".post-body.entry-content",
            ".entry-content",
            ".post-content",
            ".post-body",
            "article .content"
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                return element.text.strip()
            except:
                continue
        return None
    
    def check_bulgaria_eligible(self, description):
        """Check if Bulgaria is eligible for the opportunity"""
        try:
            if not description:
                return False
                
            description_lower = description.lower()
            eligibility_index = description_lower.find('eligibility')
            if eligibility_index == -1:
                return False
                
            eligibility_section = description_lower[eligibility_index:eligibility_index + 2000]
            
            if 'bulgaria' in eligibility_section:
                return True
            
            inclusive_terms = [
                'all countries', 'all nationalities', 'worldwide', 'global',
                'europe', 'european', 'eu countries', 'european union',
                'any country', 'any nationality', 'all nationalities',
                'erasmus', 'erasmus+', 'erasmus plus', 'youth programme countries',
                'youth workers', 'trainers', 'youth leaders', 'youth project managers', 'volunteering mentors',
            ]
            
            for term in inclusive_terms:
                if term in eligibility_section:
                    return True
                    
            return False
            
        except Exception as e:
            # print(f"⚠️ Error checking Bulgaria eligibility: {e}")
            return False
    
    def extract_location_from_title(self, post_title):
        """Extract city and country from post title"""
        country_found = None
        city_found = None
        
        try:
            # Load countries data
            with open(self.countries_path, 'r', encoding='utf-8') as f:
                countries_data = json.load(f)
                countries_list = countries_data.get("countries", [])
            
            # Load cities data  
            with open(self.cities_path, 'r', encoding='utf-8') as f:
                cities_data = json.load(f)
                cities_list = cities_data.get("cities", [])
            
            title_lower = post_title.lower()
            
            # Search for countries in title
            for country in countries_list:
                if country.lower() in title_lower:
                    country_found = country
                    break
            
            # Search for cities in title
            for city in cities_list:
                if city.lower() in title_lower:
                    city_found = city
                    break
            
            return city_found, country_found
            
        except Exception as e:
            # print(f"❌ Error extracting location from title: {e}")
            return None, None
    
    def extract_opportunity_type(self, post_title, description):
        """Extract type of opportunity"""
        text = f"{post_title.lower()} {description.lower() if description else ''}"
        
        type_keywords = {
            'competition': ['competition', 'contest', 'prize', 'award', 'challenge', 'tournament'],
            'exchange': ['exchange', 'cultural exchange', 'youth exchange', 'student exchange'],
            'event': ['event', 'conference', 'summit', 'workshop', 'seminar', 'forum', 'meeting' 'volunteering'],
            'scholarship': ['scholarship', 'grant', 'funding', 'financial aid', 'stipend'],
            'erasmus': ['erasmus', 'erasmus+', 'erasmus plus']
        }
        
        for opp_type, keywords in type_keywords.items():
            if any(keyword in text for keyword in keywords):
                return opp_type
        
        return 'event'
    
    def extract_mode_of_work(self, description):
        """Extract mode of work"""
        if not description:
            return 'on-site'
        
        text = description.lower()
        
        remote_terms = ['virtual', 'digital', 'zoom', 'webinar', 'from home']
        onsite_terms = ['on-site', 'onsite', 'in-person', 'physical', 'venue', 'location', 'face-to-face']
        hybrid_terms = ['hybrid', 'both online and in-person', 'online and onsite', 'partially remote']
        
        if any(term in text for term in hybrid_terms):
            return 'hybrid'
        elif any(term in text for term in remote_terms):
            return 'remote'
        elif any(term in text for term in onsite_terms):
            return 'on-site'
        
        return 'on-site'
    
    def extract_categories(self, post_title, description):
        """Extract categories from title and description"""
        try:
            with open(self.categories_path, 'r', encoding='utf-8') as f:
                category_data = json.load(f)
            
            text = f"{post_title.lower()} {description.lower() if description else ''}"
            matched_categories = []
            
            for category, keywords in category_data.items():
                if any(keyword in text for keyword in keywords):
                    matched_categories.append(category)
            
            return matched_categories
            
        except Exception as e:
            print(f"Error extracting categories: {e}")
            return []
        
    def extract_banner_image(self):
        """Extract banner image URL from the specified section"""
        try:
            # Look for the image inside the div with class 'separator' and the nested <a> tag
            image_element = self.driver.find_element(By.CSS_SELECTOR, 'div.separator a img')
            image_url = image_element.get_attribute('src')
            return image_url
        except Exception as e:
            print(f"⚠️ Could not extract banner image: {e}")
            return "No image found"
    
    def scrape_single_post(self, post_url, post_number):
        """Scrape data from a single post URL - ONLY SAVE IF BULGARIA ELIGIBLE"""
        try:
            print(f"📝 Processing Post {post_number}...")
            
            # Navigate to post
            self.driver.get(post_url)
            time.sleep(3)
            
            # Extract title
            try:
                title_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.post-title"))
                )
                post_title = title_element.text.strip()
            except TimeoutException:
                # print("❌ Title element not found")
                return None
            
            # Extract other data
            application_url = self.extract_opportunity_link()
            deadline = self.get_deadline_date()
            description = self.extract_description()
            
            # Check Bulgaria eligibility - THIS IS THE KEY CHECK
            is_eligible = self.check_bulgaria_eligible(description)
            
            # ONLY PROCEED IF BULGARIA IS ELIGIBLE
            if not is_eligible:
                # print("🚫 Skipping - Bulgaria not eligible")
                return None
            
            # Extract location (only if Bulgaria is eligible)
            city, country = self.extract_location_from_title(post_title)
            
            # Extract additional fields (only if Bulgaria is eligible)
            opportunity_type = self.extract_opportunity_type(post_title, description)
            mode_of_work = self.extract_mode_of_work(description)
            categories = self.extract_categories(post_title, description)
            banner_image = self.extract_banner_image()

            opportunity_data = {
                "postNo": post_number,
                "title": post_title,
                "city": city,
                "country": country,
                "description": description,
                "validUntil": deadline,
                "type": opportunity_type,
                "modeOfWork": mode_of_work,
                "categories": categories,
                "applicationUrl": application_url,
                "bannerImage": banner_image ,
            }
            
            self.bulgaria_eligible_count += 1
            print(f"✅ Saved Post {post_number} (Bulgaria Eligible)")
            return opportunity_data
            
        except Exception as e:
            # print(f"❌ Error processing Post {post_number}: {e}")
            return None
    
    def save_to_json(self, filename="opportunit4u_data.json"):
        """Save only Bulgaria-eligible data to JSON file"""
        try:
            # Create data folder if it doesn't exist
            os.makedirs(self.data_folder, exist_ok=True)
            
            # Create full file path
            file_path = os.path.join(self.data_folder, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.all_opportunities, f, indent=2, ensure_ascii=False)
            print(f"💾 Data saved to {file_path}")
            print(f"📊 Total Bulgaria-eligible opportunities: {len(self.all_opportunities)}")
        except Exception as e:
            print(f"❌ Error saving to JSON: {e}")
    
    def run(self):
        """Main function to run the scraper"""
        try:
            # Setup driver
            if not self.setup_driver():
                return
            try:
                self.driver.execute_script("document.body.style.zoom='75%'")
            except:
                pass
            # Load all posts and get URLs
            post_urls = self.load_all_posts()
            if not post_urls:
                print("❌ No post URLs found")
                return
            
            # Process each post URL
            total_posts = len(post_urls)
            for i, post_url in enumerate(post_urls, 1):
                opportunity_data = self.scrape_single_post(post_url, i)
                if opportunity_data:
                    self.all_opportunities.append(opportunity_data)
                
                # Add delay between posts to be respectful
                time.sleep(2)
            
            # Save only Bulgaria-eligible data
            self.save_to_json()
            
            print(f"\n{'='*50}")
            print(f"🎉 SCRAPING COMPLETED!")
            print(f"📊 Total posts processed: {total_posts}")
            print(f"🇧🇬 Bulgaria-eligible opportunities found: {self.bulgaria_eligible_count}")
            print(f"💾 Saved to: {os.path.join(self.data_folder, 'opportunit4u_data.json')}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"❌ Error in main execution: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                print("🔚 Driver closed")

# Run the scraper
if __name__ == "__main__":
    scraper = Opportunit4uScraper(max_load_more=0)  # Set max load more clicks
    scraper.run()