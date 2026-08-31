import requests
import re
import logging
from generate_usernames import score_username, get_priority, get_value_estimate
from db import add_to_watchlist

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_wikipedia_trending():
    # Modified to target general trending articles instead of sensitive topics (Recent Deaths) for ethical/safety reasons.
    url = "https://en.wikipedia.org/wiki/Wikipedia:Top_25_Report"
    names = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        # Basic regex to extract potential words/names from the trending table
        matches = re.findall(r'<td><a href="[^"]+" title="([^"]+)">', response.text)
        for match in matches:
            # Clean up and split by non-word characters
            words = re.split(r'\W+', match.lower())
            for word in words:
                if 2 <= len(word) <= 6 and word.isalpha():
                    names.append(word)
    except Exception as e:
        logging.error(f"Error scraping Wikipedia: {e}")
    return list(set(names))

def scrape_github_trending():
    url = "https://github.com/trending"
    names = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        # Extract repo names using regex on the href
        matches = re.findall(r'href="/[^/]+/([^/"]+)"', response.text)
        for match in matches:
            # Clean and filter to alpha only
            clean_name = re.sub(r'[^a-zA-Z]', '', match.lower())
            if 2 <= len(clean_name) <= 6:
                names.append(clean_name)
                # Generate variations
                if len(clean_name) < 6:
                    names.append(clean_name + "s")
    except Exception as e:
        logging.error(f"Error scraping GitHub: {e}")
    return list(set(names))

def run():
    logging.info("Starting trending discovery...")
    candidates = set()
    
    wiki_names = scrape_wikipedia_trending()
    logging.info(f"Found {len(wiki_names)} candidates from Wikipedia.")
    candidates.update(wiki_names)
    
    github_names = scrape_github_trending()
    logging.info(f"Found {len(github_names)} candidates from GitHub.")
    candidates.update(github_names)
    
    added_count = 0
    for name in candidates:
        if not name.isalpha() or not (2 <= len(name) <= 6):
            continue
            
        try:
            score = score_username(name)
            if score >= 35:
                priority = get_priority(name, score)
                value_est = get_value_estimate(name, score)
                
                # Add to watchlist (platform-aware logic can be extended inside db or here)
                add_to_watchlist(name, score, priority, value_est)
                added_count += 1
        except Exception as e:
            logging.error(f"Error processing or adding {name} to watchlist: {e}")
                
    logging.info(f"Finished. Added {added_count} trending names to watchlist.")

if __name__ == "__main__":
    run()
