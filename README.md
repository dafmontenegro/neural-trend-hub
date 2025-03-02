# neural-trend-hub

neural_trend_hub is an AI-powered trend analysis tool designed to scrape news articles related to a given search term and generate a detailed trend report. The report is specifically tailored to inform public figures (e.g., politicians) about what is being said about them over a defined period. The report includes key details such as the date range, location, language of the news, the total number of articles analyzed, and highlights of the most significant news items.

## Features

- **Dynamic News Scraping:**  
  Scrapes Google News for a specified search term, with automatic expansion of the date range if not enough results are found.

- **Customizable Parameters:**  
  Set parameters for search term, location, language, minimum required results, expected results per query, and date range.

- **Trend Report Generation:**  
  Uses an AI model (DeepSeek r1:1.5b via Ollama and LangChain) to generate a detailed and professional trend report in the specified language. The report includes:
  - Report title (based on the search term)
  - Date range of the news collection
  - Total number of news articles analyzed
  - Highlights of the top 3 most significant articles (title, source, and snippet)
  - Information on the location and language of the search
  - A comprehensive analysis of prevailing opinions and potential implications

- **Local LLM Integration:**  
  Integrates with the locally hosted Ollama API to invoke the DeepSeek model for generating trend reports.

## Prerequisites

- Python 3.7 or higher
- Required Python packages:
  - `requests`
  - `beautifulsoup4`
  - `langchain_ollama`
  - `logging`
  - `datetime`
  - `re`
  - `json`
- A locally running Ollama server with the DeepSeek r1:1.5b or Llama 3.2:3b model pulled.  
  You can pull the model using:
  ```bash
  !ollama pull deepseek-r1:1.5b
  !ollama pull llama3.2:3b
  ```
