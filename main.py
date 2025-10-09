import json
import os
import sys
from pathlib import Path

DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "all_opportunities.json")

FILES = [
    "opportunit4u_data.json",
    "european_youth_portal_bulgaria_eligible.json",
    "smokinya_bulgaria_eligible.json",
    "eurodesk_learning.json",
]

def run_all_scrapers():
    print("🚀 Starting Opportunity Scrapers...")
    
    try:
        # Run Eurodesk Scraper
        print("\n📊 Running Eurodesk Scraper...")
        os.system("python scrapers/eurodesk_scraper.py")

    except Exception as e:
        print(f"❌ Error running scrapers: {e}")

    try:
        # Run European Youth Portal Scraper
        print("\n📊 Running European Youth Portal Scraper...")
        os.system("python scrapers/european_youth_scraper.py")
    
    except Exception as e:
        print(f"❌ Error running scrapers: {e}")
    
    try:
        # Run Opportunit4u Scraper
        print("\n📊 Running Opportunit4u Scraper...")
        os.system("python scrapers/opportunit4u_scraper.py")
    except Exception as e:
        print(f"❌ Error running scrapers: {e}")
    try:    
        # Run Smokinya Scraper
        print("\n📊 Running Smokinya Scraper...")
        os.system("python scrapers/smokinya_scraper.py")
        print("\n✅ All scrapers completed successfully!")
    except Exception as e:
        print(f"❌ Error running scrapers: {e}")

def run_merge_script():
    """Run the merge_all_json.py script to combine and standardize all data"""
    print("\n🔄 Merging and standardizing all data...")
    try:
        # Run the merge script
        os.system("python merg_all_json.py")
        print("✅ Data merging completed successfully!")
    except Exception as e:
        print(f"❌ Error merging data: {e}")

def main():
    # Run all scrapers first
    run_all_scrapers()
    
    # Then run the merge script to combine and standardize all data
    run_merge_script()
    
    # Verify the final output file exists
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            final_data = json.load(f)
        print(f"\n🎉 FINAL RESULT: Combined {len(final_data)} opportunities into {OUTPUT_FILE}")
        
        # Show some statistics
        sources = {}
        for item in final_data:
            source = item.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        print("\n📊 SOURCE BREAKDOWN:")
        for source, count in sources.items():
            print(f"   {source}: {count} opportunities")
            
    else:
        print(f"❌ Final output file not found: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()