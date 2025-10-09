# merge_all_json.py
import json
import os
import time
from pathlib import Path
from datetime import datetime
import re

# Import the translator
from translator import translate_entry

DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "all_opportunities.json")

FILES = [
    "opportunit4u_data.json",
    "european_youth_portal_bulgaria_eligible.json",
    "smokinya_bulgaria_eligible.json",
    "eurodesk_learning.json",
]

def standardize_date(date_str):
    """
    Convert various date formats to standardized UTC format (YYYY-MM-DD).
    Returns None if date cannot be parsed.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    # Clean the date string
    date_str = date_str.strip()
    
    # Skip known non-date values
    invalid_values = [
        "No date found", "UPCOMING", "Unknown", "N/A", 
        "No application deadline", "ТЕКУЩО", "YYYY-MM-DD"
    ]
    if date_str in invalid_values:
        return None
    
    # Remove time parts and timezone info
    date_str = re.sub(r'\s+\d{1,2}:\d{2}.*$', '', date_str)  # Remove time
    date_str = re.sub(r'\s*[A-Za-z]+\s*time.*$', '', date_str)  # Remove "Brussels time" etc
    date_str = re.sub(r'\s*\d{1,2}:\d{2}.*$', '', date_str)  # Remove time with colon
    
    # Remove ordinal indicators (st, nd, rd, th)
    date_str = re.sub(r'(\d+)(st|nd|rd|th)\s+', r'\1 ', date_str)
    
    # Remove "of" from dates like "7th of October 2025"
    date_str = re.sub(r'\s+of\s+', ' ', date_str)
    
    # Try different date patterns
    patterns = [
        # YYYY-MM-DD (already standardized)
        (r'^(\d{4})-(\d{2})-(\d{2})$', lambda m: f"{m[1]}-{m[2]}-{m[3]}"),
        
        # DD/MM/YYYY
        (r'^(\d{1,2})/(\d{1,2})/(\d{4})$', lambda m: f"{m[3]}-{m[2].zfill(2)}-{m[1].zfill(2)}"),
        
        # DD Month YYYY (21 October 2025)
        (r'^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$', lambda m: parse_month_date(m[1], m[2], m[3])),
        
        # Month DD YYYY (October 21 2025)
        (r'^([A-Za-z]+)\s+(\d{1,2})\s+(\d{4})$', lambda m: parse_month_date(m[2], m[1], m[3])),
        
        # Month DD, YYYY (October 21, 2025)
        (r'^([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})$', lambda m: parse_month_date(m[2], m[1], m[3])),
        
        # YYYY only
        (r'^(\d{4})$', lambda m: f"{m[1]}-01-01"),
    ]
    
    for pattern, converter in patterns:
        match = re.match(pattern, date_str, re.IGNORECASE)
        if match:
            try:
                result = converter(match.groups())
                if result:
                    # Validate the result is a proper date
                    datetime.strptime(result, '%Y-%m-%d')
                    return result
            except (ValueError, IndexError):
                continue
    
    # Try datetime parsing as fallback with common formats
    try:
        # Common date formats to try
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%d %B %Y',
            '%B %d %Y',
            '%d %b %Y',
            '%b %d %Y',
            '%d %B, %Y',
            '%B %d, %Y',
            '%Y'
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue
    except Exception:
        pass
    
    return None

def parse_month_date(day, month_str, year):
    """Parse date with month names and return YYYY-MM-DD format"""
    month_map = {
        'january': '01', 'jan': '01',
        'february': '02', 'feb': '02', 
        'march': '03', 'mar': '03',
        'april': '04', 'apr': '04',
        'may': '05',
        'june': '06', 'jun': '06',
        'july': '07', 'jul': '07',
        'august': '08', 'aug': '08',
        'september': '09', 'sep': '09', 'sept': '09',
        'october': '10', 'oct': '10',
        'november': '11', 'nov': '11',
        'december': '12', 'dec': '12'
    }
    
    month_lower = month_str.lower()
    month_num = month_map.get(month_lower)
    if month_num:
        return f"{year}-{month_num}-{str(day).zfill(2)}"
    return None

def normalize_entry(entry, source):
    """Normalize different schemas into a unified structure."""
    # Extract raw date first
    raw_date = entry.get("validUntil") or entry.get("date")
    
    # Standardize the date
    standardized_date = standardize_date(str(raw_date) if raw_date else None)
    
    normalized = {
        "postNo": entry.get("postNo") or entry.get("card_number"),
        "title": entry.get("title"),
        "title_bg": "",  # Will be filled with translation
        "city": entry.get("city"),
        "country": entry.get("country"),
        "description": entry.get("description"),
        "description_bg": "",  # Will be filled with translation
        "validUntil": standardized_date,  # Use standardized date
        "originalDate": raw_date,  # Keep original for reference
        "type": entry.get("type") or entry.get("typeOfOpportunity"),
        "modeOfWork": entry.get("modeOfWork"),
        "categories": entry.get("categories", []),
        "applicationUrl": entry.get("applicationUrl") or entry.get("url"),
        "bannerImage": entry.get("bannerImage"),
        "bulgariaEligible": entry.get("bulgariaEligible", True),
        "source": source  # Track which file this came from
    }

    # Eurodesk has arrays for cities/countries
    if source == "eurodesk_learning.json":
        if not normalized["city"] and "cities" in entry and entry["cities"]:
            normalized["city"] = entry["cities"][0]
        if not normalized["country"] and "countries" in entry and entry["countries"]:
            normalized["country"] = entry["countries"][0]

    return normalized


def load_and_normalize(filepath):
    """Load a JSON file and normalize entries."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Some files may contain a single dict, others a list
    if isinstance(data, dict):
        data = [data]

    source = os.path.basename(filepath)
    normalized_entries = []
    
    for entry in data:
        normalized_entry = normalize_entry(entry, source)
        normalized_entries.append(normalized_entry)
    
    return normalized_entries


def main():
    all_data = []
    date_stats = {
        'total': 0,
        'standardized': 0,
        'failed': 0
    }
    
    # Create data directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)
    
    for file in FILES:
        path = os.path.join(DATA_DIR, file)
        if os.path.exists(path):
            print(f"✅ Loading {file} ...")
            try:
                entries = load_and_normalize(path)
                all_data.extend(entries)
                
                # Count date standardization results
                for entry in entries:
                    if entry.get('originalDate'):
                        date_stats['total'] += 1
                        if entry['validUntil']:
                            date_stats['standardized'] += 1
                        else:
                            date_stats['failed'] += 1
                
                print(f"   → Added {len(entries)} records.")
            except Exception as e:
                print(f"⚠️ Error processing {file}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️ Missing file: {file}")

    # Add Bulgarian translations using the translator module
    print(f"\n🔤 Translating {len(all_data)} entries to Bulgarian...")
    translation_stats = {
        'total': len(all_data),
        'titles_translated': 0,
        'descriptions_translated': 0
    }
    
    for i, entry in enumerate(all_data):
        print(f"   Translating entry {i+1}/{len(all_data)}: {entry.get('title', '')[:50]}...")
        
        # Translate the entry
        translated_entry = translate_entry(entry)
        all_data[i] = translated_entry
        
        # Update stats
        if translated_entry.get('title_bg') and translated_entry['title_bg'] != entry.get('title'):
            translation_stats['titles_translated'] += 1
        if translated_entry.get('description_bg') and translated_entry['description_bg'] != entry.get('description'):
            translation_stats['descriptions_translated'] += 1
        
        # Add small delay to avoid API rate limits
        time.sleep(1)  # 1 second delay between translations

    # Save combined JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    # Print summaries
    if date_stats['total'] > 0:
        print(f"\n📊 DATE STANDARDIZATION SUMMARY:")
        print(f"   Total entries with dates: {date_stats['total']}")
        print(f"   Successfully standardized: {date_stats['standardized']}")
        print(f"   Failed to standardize: {date_stats['failed']}")
        print(f"   Success rate: {(date_stats['standardized']/date_stats['total'])*100:.1f}%")
    
    print(f"\n🌍 TRANSLATION SUMMARY:")
    print(f"   Total entries processed: {translation_stats['total']}")
    print(f"   Titles translated: {translation_stats['titles_translated']}")
    print(f"   Descriptions translated: {translation_stats['descriptions_translated']}")

    print(f"\n🎉 Combined {len(all_data)} records into {OUTPUT_FILE}")
    print(f"✅ All entries now include Bulgarian translations!")


if __name__ == "__main__":
    main()