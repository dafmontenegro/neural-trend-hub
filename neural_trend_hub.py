from langchain_ollama import OllamaLLM
from bs4 import BeautifulSoup
import urllib.parse
import requests
import datetime
import logging
import json
import re

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

def generate_report_prompt(news_data, search_term, location, language, start_date, end_date):
    """
    Generate a prompt for the LLM to produce a trend report.
    
    The prompt instructs the LLM to analyze the provided news articles and generate a report
    intended for the person whose name was used as the search term (e.g., Gustavo Petro), 
    summarizing what has been said about them during the defined period.
    
    The report must include:
      - A title with the search term.
      - The date range of the news collection.
      - The total number of news articles analyzed.
      - The three most significant articles (listing their title, source, and snippet).
      - The location and language of the search.
      - Additional pertinent details and insights.
    
    Parameters:
        news_data (list): List of dictionaries containing the scraped news articles.
        search_term (str): The search term used.
        location (str): The geographic location code.
        language (str): The language code.
        start_date (datetime.date): The start date of the news collection.
        end_date (datetime.date): The end date of the news collection.
        
    Returns:
        str: The complete prompt for the LLM.
    """
    total_articles = len(news_data)
    # Select the first 3 articles as the "most significant"
    top_articles = news_data[:3]
    
    prompt = f"Genera un informe de tendencia profesional en {language} dirigido a {search_term}.\n\n"
    prompt += f"Título del Informe: {search_term}\n"
    prompt += f"Rango de Fechas: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}\n"
    prompt += f"Ubicación: {location}\n"
    prompt += f"Idioma de las Noticias: {language}\n"
    prompt += f"Total de Noticias Analizadas: {total_articles}\n\n"
    
    prompt += "Top 3 Noticias Más Relevantes:\n"
    for idx, article in enumerate(top_articles, start=1):
        prompt += f"{idx}. Título: {article.get('title', '')}\n"
        prompt += f"   Fuente: {article.get('source', '')}\n"
        prompt += f"   Extracto: {article.get('snippet', '')}\n\n"
    
    prompt += "Analiza las noticias anteriores y genera un informe detallado que resuma lo que se ha dicho sobre ti durante el período indicado. "
    prompt += "El informe debe ser preciso, profesional y contener los siguientes detalles:\n"
    prompt += " - Un resumen de las tendencias y opiniones predominantes.\n"
    prompt += " - Las implicaciones potenciales de las noticias para tu imagen y acciones futuras.\n"
    prompt += " - Cualquier otro detalle relevante basado en el análisis de las noticias.\n\n"
    prompt += "El informe se debe escribir de manera clara y dirigida a ti, explicando en detalle el análisis realizado con la información recopilada."
    
    return prompt

if __name__ == "__main__":
    # Set parameters for scraping: using Gustavo Petro in Colombia (español)
    search_term = "Gustavo Petro"
    location = "co"   # Colombia
    language = "es"   # Spanish
    min_results = 3
    expected_results = 15
    initial_days = 1
    
    # Scrape Google News
    news_data, start_date, end_date = scrape_google_news(search_term, location, language, min_results, expected_results, initial_days)
    
    if news_data:
        start_str = start_date.strftime("%Y_%m_%d")
        end_str = end_date.strftime("%Y_%m_%d")
        filename = f"{to_snake_case(search_term)}_{start_str}_{end_str}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Scraping complete. {len(news_data)} news articles saved to {filename}.")
        
        # Generate the prompt for the trend report
        report_prompt = generate_report_prompt(news_data, search_term, location, language, start_date, end_date)
        
        # Initialize the LLM using the deepseek-r1:1.5b model via Ollama
        llm_deepseek_r1 = OllamaLLM(model="llama3.2:3b")
        
        # Invoke the model with the prompt to generate the trend report
        trend_report = llm_deepseek_r1.invoke(report_prompt)
        
        # Save the generated trend report to a text file
        report_filename = f"{to_snake_case(search_term)}_trend_report_{start_str}_{end_str}.txt"
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(trend_report)
        
        logging.info(f"Trend report generated and saved to {report_filename}.")
    else:
        logging.info("No news articles were retrieved.")
