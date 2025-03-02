import json
import requests
from bs4 import BeautifulSoup
import datetime
import urllib.parse

def build_google_news_url(query, start_date, end_date):
    """
    Build the Google News search URL using a specific query and date range.
    
    Parameters:
        query (str): The search term.
        start_date (datetime.date): The start date for filtering news.
        end_date (datetime.date): The end date for filtering news.
    
    Returns:
        str: The constructed URL.
    """
    base_url = "https://www.google.com/search"
    # Format dates as mm/dd/yyyy
    cd_min = start_date.strftime("%m/%d/%Y")
    cd_max = end_date.strftime("%m/%d/%Y")
    
    params = {
        'q': query,
        'gl': 'us',
        'tbm': 'nws',
        'num': '100',  # Request up to 100 results per page
        'tbs': f"cdr:1,cd_min:{cd_min},cd_max:{cd_max}"
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    print(url)
    return url

def scrape_news(query, days=1):
    """
    Scrape Google News for a specific query within the last n days.
    
    Parameters:
        query (str): The search term.
        days (int): Number of days in the past to include news.
    
    Returns:
        list: A list of dictionaries containing news data.
    """
    # Calculate date range from 'days' ago until today.
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)
    
    url = build_google_news_url(query, start_date, end_date)
    
    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
        "(KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    
    news_results = []
    # Use the provided selectors to extract news data
    for el in soup.select("div.SoaBEf"):
        news_results.append({
            "link": el.find("a")["href"],
            "title": el.select_one("div.MBeuO").get_text() if el.select_one("div.MBeuO") else "",
            "snippet": el.select_one(".GI74Re").get_text() if el.select_one(".GI74Re") else "",
            "date": el.select_one(".LfVVr").get_text() if el.select_one(".LfVVr") else "",
            "source": el.select_one(".NUnG9d span").get_text() if el.select_one(".NUnG9d span") else ""
        })
    
    return news_results

if __name__ == "__main__":
    # Example usage
    search_term = input("Enter the search term: ")
    days = int(input("Enter the number of days to search back: "))
    
    news_data = scrape_news(search_term, days)
    
    # Save the news data to a JSON file
    output_file = "news_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(news_data, f, ensure_ascii=False, indent=2)
    
    print(f"Scraping complete. {len(news_data)} news articles saved to {output_file}.")
