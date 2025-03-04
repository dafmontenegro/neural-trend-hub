from langchain_ollama import OllamaLLM
from bs4 import BeautifulSoup
import urllib.parse
import requests
import datetime
import logging
import json
import re
import os

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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

def build_google_news_url(query, start_date, end_date, num_results, location, language):
    """
    Build the Google News search URL using a specific query, date range, location, and language.
    
    Parameters:
        query (str): The search term.
        start_date (datetime.date): The start date for filtering news.
        end_date (datetime.date): The end date for filtering news.
        num_results (int): Number of results to request.
        location (str): Geographic location code (e.g., "co" for Colombia).
        language (str): Language code (e.g., "es" for Spanish).
    
    Returns:
        str: The constructed URL.
    """
    base_url = "https://www.google.com/search"
    # Format dates as mm/dd/yyyy
    cd_min = start_date.strftime("%m/%d/%Y")
    cd_max = end_date.strftime("%m/%d/%Y")
    
    params = {
        'q': query,
        'gl': location,      # geographic location code (e.g., "co")
        'hl': language,      # language code (e.g., "es")
        'tbm': 'nws',
        'num': str(num_results),
        'tbs': f"cdr:1,cd_min:{cd_min},cd_max:{cd_max}"
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return url

def scrape_google_news(search_term, location="co", language="es", min_results=10, expected_results=100, days=1):
    """
    Scrape Google News for a given search term with dynamic date range expansion if necessary.
    
    Parameters:
        search_term (str): The search term to query.
        location (str): Geographic location code (default "co" for Colombia).
        language (str): Language code (default "es" for Spanish).
        min_results (int): Minimum number of results required (default 10).
        expected_results (int): Expected number of results per page (default 100).
        days (int): Initial number of days in the past to include news (default 1).
        
    Returns:
        tuple: (final_news, used_start_date, used_end_date)
            - final_news (list): A list of dictionaries containing news data.
            - used_start_date (datetime.date): The start date used.
            - used_end_date (datetime.date): The end date used.
    """
    candidate_ranges = [days, 7, 30, 90]
    final_news = []
    used_range = None

    for candidate_days in candidate_ranges:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=candidate_days)
        url = build_google_news_url(search_term, start_date, end_date, expected_results, location, language)
        
        logging.info(f"Generated URL for {candidate_days}-day range:")
        logging.info(url)
        
        headers = {
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            continue
        
        soup = BeautifulSoup(response.content, "html.parser")
        news_results = []
        
        # Use the provided selectors to extract news data
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
        
        logging.info(f"Found {len(news_results)} articles for a {candidate_days}-day range.")
        if len(news_results) >= min_results or candidate_days == candidate_ranges[-1]:
            final_news = news_results
            used_range = (start_date, end_date)
            break
        else:
            logging.info("Not enough articles found, expanding the time range...")

    return final_news, used_range[0], used_range[1]

def generate_report_prompt(news_data, search_term, location, language, start_date, end_date, output_language):
    """
    Generate a prompt for the LLM to produce a trend report.
    
    Parameters:
        news_data (list): List of dictionaries containing the scraped news articles.
        search_term (str): The search term used.
        location (str): The geographic location code.
        language (str): The language code of the news.
        start_date (datetime.date): The start date of the news collection.
        end_date (datetime.date): The end date of the news collection.
        output_language (str): The language to write the report in.
        
    Returns:
        str: The complete prompt for the LLM.
    """
    total_articles = len(news_data)
    # Select the first 3 articles as the "most significant"
    top_articles = news_data[:3]
    
    prompt = f"Generate a professional trend report in {output_language} addressed to {search_term}.\n\n"
    prompt += f"Report Title: {search_term}\n"
    prompt += f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n"
    prompt += f"Location: {location}\n"
    prompt += f"News Language: {language}\n"
    prompt += f"Total News Articles Analyzed: {total_articles}\n\n"
    
    prompt += "Top 3 Most Relevant News Articles:\n"
    for idx, article in enumerate(top_articles, start=1):
        prompt += f"{idx}. Title: {article.get('title', '')}\n"
        prompt += f"   Source: {article.get('source', '')}\n"
        prompt += f"   Snippet: {article.get('snippet', '')}\n\n"
    
    prompt += f"Analyze ALL {total_articles} news articles comprehensively. "
    prompt += "Generate a detailed report summarizing what has been said about you during the indicated period. "
    prompt += "The report must be precise, professional, and contain the following details:\n"
    prompt += " - A summary of predominant trends and opinions across ALL collected news articles.\n"
    prompt += " - The potential implications of the news for your image and future actions.\n"
    prompt += " - A comprehensive analysis that goes beyond the top 3 articles.\n\n"
    prompt += "The report should be written clearly and addressed to you, explaining in detail the analysis performed with the collected information.\n\n"
    prompt += "IMPORTANT: The output must be in plain text format without any special formatting like bold, italics, or markdown. "
    prompt += "Write the report as continuous text with appropriate paragraph breaks.\n\n"
    prompt += "SECTION: TOP 3 MOST SIGNIFICANT ARTICLES (for quick reference)\n"
    for idx, article in enumerate(top_articles, start=1):
        prompt += f"{idx}. Comprehensive Summary:\n"
        prompt += f"   Title: {article.get('title', '')}\n"
        prompt += f"   Source: {article.get('source', '')}\n"
        prompt += f"   Key Points: [Provide a concise, insightful summary of the article's main message and potential impact]\n\n"
    
    return prompt

def create_folder_structure(base_folder, search_term):
    """
    Create organized folder structure for reports.
    
    Parameters:
        base_folder (str): Base folder name for reports.
        search_term (str): The search term used.
        
    Returns:
        str: Path to the reports folder.
    """
    reports_folder = os.path.join(base_folder, to_snake_case(search_term))
    if not os.path.exists(reports_folder):
        os.makedirs(reports_folder)
    return reports_folder

if __name__ == "__main__":
    # Set parameters for scraping:
    search_term = "Donald Trump"
    location = "us"   # United States
    language = "en"   # English
    output_languages = ["en"]  # Multiple output languages
    min_results = 10
    expected_results = 100
    initial_days = 1
    
    # Define base folder for reports
    base_folder = "reports"
    reports_folder = create_folder_structure(base_folder, search_term)
    
    # Scrape Google News
    news_data, start_date, end_date = scrape_google_news(
        search_term, location, language, min_results, expected_results, initial_days
    )
    
    if news_data:
        # Get current timestamp for filename
        current_time = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        start_str = start_date.strftime("%Y_%m_%d")
        end_str = end_date.strftime("%Y_%m_%d")
        
        # Save scraped news data
        json_filename = os.path.join(
            reports_folder, 
            f"{to_snake_case(search_term)}_{start_str}_{end_str}_{current_time}_en.json"
        )
        
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Scraping complete. {len(news_data)} news articles saved to {json_filename}.")
        
        # List of LLMs to use
        llm_list = [
            {"name": "deepseek-r1:1.5b", "model": "deepseek-r1:1.5b"},
            {"name": "llama3.2:3b", "model": "llama3.2:3b"},
            {"name": "phi3.5:3.8b", "model": "phi3.5:3.8b"}
        ]
        
        # Generate reports for each output language
        for output_language in output_languages:
            # Generate the prompt for the trend report
            report_prompt = generate_report_prompt(
                news_data, search_term, location, language, start_date, end_date, output_language
            )
            
            # Generate reports with each LLM
            for llm_info in llm_list:
                try:
                    # Initialize the specific LLM
                    llm = OllamaLLM(model=llm_info["model"])
                    
                    # Invoke the model with the prompt to generate the trend report
                    trend_report = llm.invoke(report_prompt)
                    
                    # Save the generated trend report to a text file with LLM name and language in filename
                    report_filename = os.path.join(
                        reports_folder,
                        f"{to_snake_case(search_term)}_trend_report_{start_str}_{end_str}_{current_time}_{llm_info['name'].replace(':', '_')}_{output_language}.txt"
                    )
                    
                    with open(report_filename, "w", encoding="utf-8") as f:
                        f.write(trend_report)
                    
                    logging.info(f"Trend report generated using {llm_info['name']} in {output_language} and saved to {report_filename}.")
                    
                except Exception as e:
                    logging.error(f"Error generating report with {llm_info['name']} in {output_language}: {e}")
    else:
        logging.info("No news articles were retrieved.")