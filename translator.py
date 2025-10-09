import json
import os
import sys
from pathlib import Path
from openai import OpenAI

# ---------------------------
# Project paths (same as your other files)
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent.parent   # project root
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"

# Add the project root directory to path
sys.path.append(str(BASE_DIR))

# Import API key from config.config
try:
    from config.config import OPENAI_API_KEY
    print("✅ Successfully imported OPENAI_API_KEY from config")
except ImportError as e:
    print("❌ Could not import OPENAI_API_KEY from config/config.py")
    print(f"Error: {e}")
    OPENAI_API_KEY = None


class BulgarianTranslator:
    def __init__(self):
        self.client = self.setup_openai_client()
        
    def setup_openai_client(self):
        """Setup OpenAI client with API key"""
        if not OPENAI_API_KEY:
            print("❌ OPENAI_API_KEY not found in config.py")
            return None
        
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            # Test the connection with a simple request
            test_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Translate 'hello' to Bulgarian"}],
                max_tokens=10
            )
            print("✅ OpenAI translator client configured successfully")
            return client
        except Exception as e:
            print(f"❌ Failed to setup OpenAI translator client: {e}")
            return None
    
    def translate_text(self, text, text_type="text"):
        """
        Translate text to Bulgarian using OpenAI GPT
        text_type: "title" or "description" for better context
        """
        if not text or not self.client:
            return text
        
        # Skip translation for common placeholder texts
        skip_texts = [
            "No description found", "No title found", "No description", 
            "N/A", "No image found", "No URL found", "No date found"
        ]
        if text in skip_texts:
            return text
        
        try:
            # Create context-based prompt
            if text_type == "title":
                prompt = f"""
                Translate this opportunity title to Bulgarian. Keep it concise and natural.
                Return ONLY the Bulgarian translation, no explanations.
                
                Title: "{text}"
                
                Bulgarian translation:
                """
            else:  # description
                # Limit description length to avoid token limits
                if len(text) > 3000:
                    text = text[:3000] + "..."
                
                prompt = f"""
                Translate this opportunity description to Bulgarian. 
                Keep the meaning accurate and maintain a professional tone.
                Return ONLY the Bulgarian translation, no explanations.
                
                Description: "{text}"
                
                Bulgarian translation:
                """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional translator specializing in English to Bulgarian translation for educational and opportunity content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000 if text_type == "description" else 100
            )
            
            translated_text = response.choices[0].message.content.strip()
            
            # Clean up any quotes or extra spaces
            translated_text = translated_text.strip('"\' ')
            
            return translated_text
            
        except Exception as e:
            print(f"⚠️ Translation error for {text_type}: {e}")
            return text
    
    def translate_entry(self, entry):
        """Add Bulgarian translations to an entry"""
        if not self.client:
            print("❌ OpenAI client not available for translation")
            return entry
        
        print(f"🔤 Translating: {entry.get('title', '')[:50]}...")
        
        # Translate title
        if entry.get('title'):
            entry['title_bg'] = self.translate_text(entry['title'], "title")
        
        # Translate description
        if entry.get('description'):
            entry['description_bg'] = self.translate_text(entry['description'], "description")
        
        return entry

# Singleton instance
translator = BulgarianTranslator()

def translate_to_bulgarian(text, text_type="text"):
    """Convenience function for single text translation"""
    return translator.translate_text(text, text_type)

def translate_entry(entry):
    """Convenience function for entry translation"""
    return translator.translate_entry(entry)

if __name__ == "__main__":
    # Test the translator
    test_text = "Youth exchange program in Sofia"
    translated = translate_to_bulgarian(test_text, "title")
    print(f"Test translation: '{test_text}' -> '{translated}'")