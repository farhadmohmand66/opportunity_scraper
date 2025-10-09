import json
import re
import time
import os
import sys
from pathlib import Path
import tkinter as tk
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from datetime import datetime
import openai
from openai import OpenAI

# ---------------------------
# Project paths
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent.parent   # project root
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"

# Add config directory to path
sys.path.append(str(CONFIG_DIR))

# Import API key from config/config.py
try:
    from config import OPENAI_API_KEY
except ImportError as e:
    print("❌ Could not import OPENAI_API_KEY from config/config.py")
    print(f"Error: {e}")
    OPENAI_API_KEY = None

class SmokinyaScraper:
    def __init__(self):
        self.driver = None
        self.all_opportunities = []
        self.data_folder = DATA_DIR   # always points to /data
        self.client = self.setup_openai_client()
        
    def setup_openai_client(self):
        """Setup OpenAI client with API key"""
        if not OPENAI_API_KEY:
            print("❌ OPENAI_API_KEY not found in config.py")
            return None
        
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            # Test the connection
            test_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say 'OK'"}],
                max_tokens=5
            )
            print("✅ OpenAI client configured successfully")
            return client
        except Exception as e:
            print(f"❌ Failed to setup OpenAI client: {e}")
            return None
    
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
    
    def extract_all_post_links(self):
        """Extract all post links from Smokinya website"""
        post_links = []
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "div.featured-posts-content a")
            
            for link in links:
                href = link.get_attribute("href")
                if href and href not in post_links:
                    post_links.append(href)
                    print(f"✅ Found post: {href}")
            
            print(f"📊 Total post links found: {len(post_links)}")
            return post_links
            
        except Exception as e:
            print(f"❌ Error extracting post links: {e}")
            return []
    
    def extract_title(self):
        """Extract post title"""
        try:
            title_element = self.driver.find_element(By.CSS_SELECTOR, "h1.header-post-title-class")
            return title_element.text.strip()
        except:
            return None
    
    def extract_application_url(self):
        """Extract application URL"""
        try:
            application_link = self.driver.find_element(By.XPATH, "//a[contains(translate(., 'APPLICATION', 'application'), 'application')]")
            return application_link.get_attribute("href")
        except NoSuchElementException:
            return self.driver.current_url
    
    def extract_description(self):
        """Extract post description"""
        try:
            entry_content = self.driver.find_element(By.CLASS_NAME, "entry-content")
            all_paragraphs = entry_content.find_elements(By.TAG_NAME, "p")
            description = [p.text for p in all_paragraphs if p.text.strip()]
            return "\n".join(description)
        except:
            return None
        
    def extract_banner_image(self):
        """Extract the topmost image URL from the div with class 'entry-content'"""
        try:
            # Look for the first image inside the div with class 'entry-content'
            image_element = self.driver.find_element(By.CSS_SELECTOR, 'div.entry-content img')
            image_url = image_element.get_attribute('src')
            return image_url
        except Exception as e:
            print(f"⚠️ Could not extract banner image: {e}")
            return "No image found"
    
    def extract_opportunity_data_with_openai(self, description, title):
        """Use OpenAI to extract structured data from opportunity description"""
        if not self.client:
            print("❌ OpenAI client not available")
            return None
            
        try:
            categories_list = [
                "Programming", "Business and Entrepreneurship", "Marketing, Advertising, PR", 
                "Journalism", "Trade and Sales", "Psychology", "Cinema and Theater", 
                "Finance and Banking", "Design", "Music and Arts", "Social Causes", 
                "Medicine and Pharmacy", "Ecology", "Languages", "Career Guidance", 
                "Science", "Politics", "Architecture and Civil Engineering", 
                "Accelerator programs", "Health", "Environment"
            ]
            
            prompt = f"""
            Analyze this opportunity and extract structured data as JSON:
            
            TITLE: {title}
            DESCRIPTION: {description}
            
            EXTRACT THESE FIELDS:
            
            1. typeOfOpportunity: Choose from: competition, exchange, event, scholarship, erasmus, volunteering, training, internship, fellowship, conference, workshop
            
            2. modeOfWork: Choose from: remote, on-site, hybrid
            
            3. categories: Select from this EXACT list (choose maximum 3 most relevant):
            {json.dumps(categories_list, indent=2)}
            - ONLY use these exact category names
            - Choose categories that best match the opportunity's focus
            
            4. city: The city where the opportunity physically takes place
            - Look for: "hosted in [city]", "venue: [city]", "based in [city]", "location: [city]"
            - For scholarships: the university/organization's city
            - For events: the host city
            - For remote: the organization's headquarters city
            
            5. country: The country where the opportunity is located
            - Same logic as city but for country level
            
            6. validUntil: Application deadline in YYYY-MM-DD format
            - Look for: "deadline", "apply by", "application until", "closing date"
            
            7. bulgariaEligible: true/false
            - true if: mentions Bulgaria specifically, says "all countries", "worldwide", "European", "international"
            - false if: lists specific countries excluding Bulgaria
            
            Return ONLY valid JSON, no other text.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You extract structured data from opportunities. Return only JSON. For categories, strictly use only the provided list names."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1800,
                timeout=30
            )
            
            result_text = response.choices[0].message.content.strip()
            extracted_data = json.loads(result_text)
            
            print("✅ OpenAI extraction successful")
            return extracted_data
            
        except Exception as e:
            print(f"❌ OpenAI extraction error: {e}")
            return None
    
    def scrape_single_post(self, post_url, post_number):
        """Scrape data from a single post URL"""
        try:
            print(f"\n{'='*50}")
            print(f"📝 Processing Post {post_number}")
            print(f"{'='*50}")
            print(f"🔗 Navigating to: {post_url}")
            
            # Navigate to post
            self.driver.get(post_url)
            time.sleep(3)
            
            # Extract basic data
            title = self.extract_title()
            application_url = self.extract_application_url()
            description = self.extract_description()
            banner_image = self.extract_banner_image()
            print(f"🖼️ Banner image: {banner_image}")
            
            print(f"📝 Title: {title}")
            print(f"🔗 Application URL: {application_url}")
            print(f"📄 Description length: {len(description) if description else 0}")
            
            # Use OpenAI to extract structured data
            extracted_data = self.extract_opportunity_data_with_openai(description, title)
            
            if not extracted_data:
                print("❌ Failed to extract data with OpenAI")
                return None
            
            print(f"📍 Location: {extracted_data.get('city')}, {extracted_data.get('country')}")
            print(f"🎯 Type: {extracted_data.get('typeOfOpportunity')}")
            print(f"💼 Mode: {extracted_data.get('modeOfWork')}")
            print(f"📂 Categories: {extracted_data.get('categories', [])}")
            print(f"📅 Deadline: {extracted_data.get('validUntil')}")
            print(f"🇧🇬 Bulgaria Eligible: {extracted_data.get('bulgariaEligible')}")

            
            # Only save if Bulgaria is eligible
            if not extracted_data.get('bulgariaEligible'):
                print("🚫 Skipping - Bulgaria not eligible")
                return None
            
            # Create opportunity data
            opportunity_data = {
                "postNo": post_number,
                "title": title,
                "city": extracted_data.get("city"),
                "country": extracted_data.get("country"),
                "description": description,
                "validUntil": extracted_data.get("validUntil"),
                "type": extracted_data.get("typeOfOpportunity"),
                "modeOfWork": extracted_data.get("modeOfWork"),
                "categories": extracted_data.get("categories", []),
                "applicationUrl": application_url,
                # "postUrl": post_url,
                "bannerImage": banner_image,
                "bulgariaEligible": extracted_data.get("bulgariaEligible", False)
            }
            
            print(f"✅ Successfully processed Post {post_number}")
            return opportunity_data
            
        except Exception as e:
            print(f"❌ Error processing Post {post_number}: {e}")
            return None
    
    def save_to_json(self, filename="smokinya_bulgaria_eligible.json"):
        """Save Bulgaria-eligible data to JSON file in /data"""
        try:
            self.data_folder.mkdir(parents=True, exist_ok=True)
            file_path = self.data_folder / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.all_opportunities, f, indent=2, ensure_ascii=False)

            print(f"💾 Bulgaria-eligible data saved to: {file_path}")
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
            URL = "https://smokinya.com/"
            print(f"🌐 Navigating to {URL}")
            self.driver.get(URL)
            time.sleep(5)
            try:
                self.driver.execute_script("document.body.style.zoom='75%'")
            except:
                pass
            # Extract all post links
            post_links = self.extract_all_post_links()
            
            if not post_links:
                print("❌ No post links found")
                return
            
            # Process each post
            successful_posts = 0
            for i, post_link in enumerate(post_links, 1):
                opportunity_data = self.scrape_single_post(post_link, i)
                if opportunity_data:
                    self.all_opportunities.append(opportunity_data)
                    successful_posts += 1
                
                # Add delay between requests
                time.sleep(2)
            
            # Save only Bulgaria-eligible data
            self.save_to_json()
            
            print(f"\n{'='*50}")
            print(f"🎉 SCRAPING COMPLETED!")
            print(f"📊 Total posts processed: {len(post_links)}")
            print(f"🇧🇬 Bulgaria-eligible opportunities found: {successful_posts}")
            print(f"💾 Data saved to: {os.path.join(self.data_folder, 'smokinya_bulgaria_eligible.json')}")
            print(f"{'='*50}")
            
        except Exception as e:
            print(f"❌ Error in main execution: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                print("🔚 Driver closed")

# Create config.py file with API key (run this once)
def create_config_file():
    """Create config.py file for API key"""
    config_content = '''# config.py
OPENAI_API_KEY = "your-openai-api-key-here"
'''
    
    with open("config.py", "w") as f:
        f.write(config_content)
    print("✅ config.py created. Please add your OpenAI API key.")

if __name__ == "__main__":
    scraper = SmokinyaScraper()
    scraper.run()
