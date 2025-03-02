import json
import requests
from bs4 import BeautifulSoup
import datetime
import urllib.parse
import re
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def build_google_news_url(query, start_date, end_date, num_results=100):
    """
    Build the Google News search URL using a specific query, date range, and language.

    Parameters:
        query (str): The search term.
        start_date (datetime.date): The start date for filtering news.
        end_date (datetime.date): The end date for filtering news.
        num_results (int): Number of results to request (default 100).

    Returns:
        str: The constructed URL.
    """
    base_url = "https://www.google.com/search"
    # Format dates as mm/dd/yyyy
    cd_min = start_date.strftime("%m/%d/%Y")
    cd_max = end_date.strftime("%m/%d/%Y")
    
    params = {
        'q': query,
        'gl': 'us',       # geographic location (puedes modificarlo si es necesario)
        'hl': 'es',       # force language to Spanish
        'tbm': 'nws',
        'num': str(num_results),
        'tbs': f"cdr:1,cd_min:{cd_min},cd_max:{cd_max}"
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return url

def scrape_news(query, days=1, num_results=100):
    """
    Scrape Google News for a specific query within the last n days.

    Parameters:
        query (str): The search term.
        days (int): Number of days in the past to include news.
        num_results (int): Number of results to request.

    Returns:
        tuple: A tuple containing:
            - list: A list of dictionaries containing news data.
            - datetime.date: The start date used.
            - datetime.date: The end date used.
    """
    # Calculate date range from 'days' ago until today.
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)
    
    url = build_google_news_url(query, start_date, end_date, num_results)
    
    # Display the generated URL in an organized format
    logging.info(f"Generated URL: {url}")
    
    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
        "(KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        return [], start_date, end_date
    
    soup = BeautifulSoup(response.content, "html.parser")
    
    news_results = []
    # Use provided selectors to extract news data
    for el in soup.select("div.SoaBEf"):
        try:
            link = el.find("a")["href"]
            title = el.select_one("div.MBeuO").get_text() if el.select_one("div.MBeuO") else ""
            snippet = el.select_one(".GI74Re").get_text() if el.select_one(".GI74Re") else ""
            date_text = el.select_one(".LfVVr").get_text() if el.select_one(".LfVVr") else ""
            source = el.select_one(".NUnG9d span").get_text() if el.select_one(".NUnG9d span") else ""
            
            news_results.append({
                "link": link,
                "title": title,
                "snippet": snippet,
                "date": date_text,
                "source": source
            })
        except Exception as parse_error:
            logging.warning(f"Error parsing an element: {parse_error}")
            continue

    return news_results, start_date, end_date

def to_snake_case(text):
    """
    Convert a string to snake_case.

    Parameters:
        text (str): The input text.

    Returns:
        str: The text converted to snake_case.
    """
    text = text.lower().strip()
    text = re.sub(r'\W+', '_', text)
    return text

if __name__ == "__main__":
    search_term = "gustavo petro"
    candidate_ranges = [1, 7, 30, 90]
    min_required = 10
    final_news = []
    used_range = None

    for days in candidate_ranges:
        logging.info(f"Scraping news for the past {days} day(s)...")
        news_data, start_date, end_date = scrape_news(search_term, days)
        logging.info(f"Found {len(news_data)} articles for a {days}-day range.")
        if len(news_data) >= min_required or days == candidate_ranges[-1]:
            final_news = news_data
            used_range = (start_date, end_date)
            break
        else:
            logging.info("Not enough articles found, expanding the time range...")

    if final_news:
        # Generate filename with search term and date range in snake case
        start_str = used_range[0].strftime("%Y_%m_%d")
        end_str = used_range[1].strftime("%Y_%m_%d")
        filename = f"{to_snake_case(search_term)}_{start_str}_{end_str}.json"
        
        # Save the news data to a JSON file
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(final_news, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Scraping complete. {len(final_news)} news articles saved to {filename}.")
    else:
        logging.info("No news articles were retrieved.")
