from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re
import json
import time
import random

app = Flask(__name__)

def extract_from_instagram(url):
    """Improved Instagram scraping with multiple fallback methods."""
    # Generate a random user agent
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
    ]
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }
    
    try:
        # Method 1: Direct HTML scraping
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try different meta tags that might contain the caption
        meta_tags = [
            soup.find('meta', attrs={'property': 'og:description'}),
            soup.find('meta', attrs={'name': 'description'}),
            soup.find('meta', attrs={'property': 'twitter:description'})
        ]
        
        for tag in meta_tags:
            if tag and tag.get('content'):
                return tag.get('content')
        
        # Method 2: Look for JSON data in script tags
        for script in soup.find_all('script', type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if 'caption' in data:
                    return data['caption']
                if 'description' in data:
                    return data['description']
            except:
                pass
        
        # Method 3: Look for the text in a paragraph
        captions = soup.select('div.C4VMK span')
        if captions:
            return captions[0].text
            
    except Exception as e:
        print(f"Error extracting from Instagram: {str(e)}")
    
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    caption = None
    if request.method == 'POST':
        url = request.form['url']
        try:
            # Try to extract caption from Instagram
            raw_caption = extract_from_instagram(url)
            
            if raw_caption:
                # Simple direct approach - only allow safe ASCII characters
                clean_text = ''
                
                # First, handle any known emoji sequences and common non-ASCII characters
                # This prevents the script from breaking on specific emoji combinations
                safe_raw = ''
                skip_next = 0
                for i in range(len(raw_caption)):
                    if skip_next > 0:
                        skip_next -= 1
                        continue
                        
                    # Skip variation selectors and zero-width joiners that cause errors
                    if i < len(raw_caption)-1 and ord(raw_caption[i+1]) in [65039, 8205]:  # Variation selector-16 or ZWJ
                        safe_raw += raw_caption[i]
                        skip_next = 1
                    else:
                        safe_raw += raw_caption[i]
                
                # Now process the cleaned text
                for char in safe_raw:
                    if ord(char) < 128:  # ASCII range
                        clean_text += char
                    else:
                        # Try common character replacements
                        if char in 'üöäßéèêëàâôùûçñ':
                            clean_text += {'ü':'u', 'ö':'o', 'ä':'a', 'ß':'ss', 'é':'e', 'è':'e', 
                                           'ê':'e', 'ë':'e', 'à':'a', 'â':'a', 'ô':'o', 'ù':'u', 
                                           'û':'u', 'ç':'c', 'ñ':'n'}[char]
                        # Handle common emoji - with error protection
                        elif char in '🚨❌✅👀👆🔴⚪🤝📱📢🔜🏆':  # Removed problematic emoji
                            emoji_dict = {
                                '🚨':'[BREAKING] ', '❌':'[X] ', '✅':'[CHECK] ', '👀':'[EYES] ',
                                '👆':'[POINT UP] ', '🔴':'[RED] ', '⚪':'[WHITE] ',
                                '🤝':'[HANDSHAKE] ', '📱':'[PHONE] ', '📢':'[ANNOUNCEMENT] ', 
                                '🔜':'[SOON] ', '🏆':'[TROPHY] '
                            }
                            if char in emoji_dict:
                                clean_text += emoji_dict[char]
                
                # Remove any extra whitespace and quotes
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                
                # Extract just the caption from common Instagram patterns
                if ': "' in clean_text:
                    caption_part = clean_text.split(': "', 1)[1]
                    if caption_part.endswith('"'):
                        caption_part = caption_part[:-1]
                    clean_text = caption_part
                
                caption = clean_text
            else:
                caption = 'Caption not found. Instagram has strong anti-scraping measures. Try a different post or copy the caption manually.'
                
        except Exception as e:
            # Generic and safe error message that doesn't expose technical details
            caption = 'Error: Could not extract caption. Please try another Instagram post URL.'
            print(f"Error extracting caption: {str(e)}")
    
    return render_template('index.html', caption=caption)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
