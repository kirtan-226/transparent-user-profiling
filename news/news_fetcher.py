import requests
import os
from datetime import datetime
import json

# News API configuration
# Get your API key from https://newsapi.org/
NEWS_API_KEY = os.environ.get('NEWS_API_KEY', '758c48dbb96c4f96b40fd091e07070ac')
NEWS_API_BASE_URL = 'https://newsapi.org/v2'


# Uncomment this line to always use sample data (for testing)
# ALWAYS_USE_SAMPLE = True

def get_top_news(category='general', country='us', page_size=10):
    """
    Fetch top headlines from News API

    Args:
        category (str): News category
        country (str): Country code
        page_size (int): Number of articles to return

    Returns:
        list: List of news articles
    """
    # If sample mode is enabled, always return sample data
    if 'ALWAYS_USE_SAMPLE' in globals() and ALWAYS_USE_SAMPLE:
        print("Using sample news data (ALWAYS_USE_SAMPLE is True)")
        return get_sample_news()

    try:
        # Check if API key is properly set
        if NEWS_API_KEY == 'your_news_api_key':
            print("WARNING: You're using the default API key placeholder. Set your actual News API key.")
            return get_sample_news()

        url = f"{NEWS_API_BASE_URL}/top-headlines"
        params = {
            'category': category,
            'country': country,
            'pageSize': page_size,
            'apiKey': NEWS_API_KEY
        }

        print(f"Fetching news from {url} with params: {params}")
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            print(f"Successfully fetched {len(articles)} articles")

            # Add timestamp for when the news was fetched
            for article in articles:
                article['fetched_at'] = datetime.now().isoformat()

            # Cache the result to reduce API calls (optional)
            cache_articles(category, country, articles)

            return articles
        else:
            print(f"News API error: {response.status_code}, {response.text}")
            # Return cached results if API fails
            cached = get_cached_articles(category, country)
            if cached:
                print(f"Using {len(cached)} cached articles")
                return cached
            else:
                print("No cache available, using sample news")
                return get_sample_news()
    except Exception as e:
        print(f"Error fetching news: {e}")
        # Try to use cached data first, then fallback to sample data
        cached = get_cached_articles(category, country)
        if cached:
            print(f"Using {len(cached)} cached articles")
            return cached
        else:
            print("No cache available, using sample news")
            return get_sample_news()


def get_news_by_query(query, from_date=None, to_date=None, language='en', sort_by='publishedAt', page_size=10):
    """
    Search for news articles by keyword or phrase

    Args:
        query (str): Keywords or phrases to search for
        from_date (str): A date in ISO format (e.g. 2023-12-01)
        to_date (str): A date in ISO format (e.g. 2023-12-31)
        language (str): Two-letter ISO-639-1 code (e.g. 'en' for English)
        sort_by (str): 'relevancy', 'popularity', or 'publishedAt'
        page_size (int): Number of articles to return

    Returns:
        list: List of news articles matching the query
    """
    try:
        url = f"{NEWS_API_BASE_URL}/everything"
        params = {
            'q': query,
            'language': language,
            'sortBy': sort_by,
            'pageSize': page_size,
            'apiKey': NEWS_API_KEY
        }

        if from_date:
            params['from'] = from_date

        if to_date:
            params['to'] = to_date

        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])

            # Add timestamp
            for article in articles:
                article['fetched_at'] = datetime.now().isoformat()

            return articles
        else:
            print(f"News API error: {response.status_code}, {response.text}")
            return []
    except Exception as e:
        print(f"Error searching news: {e}")
        return []


def get_news_by_source(source_id='bbc-news', page_size=10):
    """
    Fetch news from a specific source

    Args:
        source_id (str): ID of the news source
        page_size (int): Number of articles to return

    Returns:
        list: List of news articles from the source
    """
    try:
        url = f"{NEWS_API_BASE_URL}/top-headlines"
        params = {
            'sources': source_id,
            'pageSize': page_size,
            'apiKey': NEWS_API_KEY
        }

        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            return data.get('articles', [])
        else:
            print(f"News API error: {response.status_code}, {response.text}")
            return []
    except Exception as e:
        print(f"Error fetching news by source: {e}")
        return []


def get_news_sources(category=None, language='en', country=None):
    """
    Get available news sources

    Args:
        category (str): News category filter
        language (str): Language filter
        country (str): Country filter

    Returns:
        list: List of news sources
    """
    try:
        url = f"{NEWS_API_BASE_URL}/sources"
        params = {
            'apiKey': NEWS_API_KEY
        }

        if category:
            params['category'] = category
        if language:
            params['language'] = language
        if country:
            params['country'] = country

        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            return data.get('sources', [])
        else:
            print(f"News API error: {response.status_code}, {response.text}")
            return []
    except Exception as e:
        print(f"Error fetching news sources: {e}")
        return []


def get_news_categories():
    """Return available news categories"""
    return ['business', 'entertainment', 'general', 'health', 'science', 'sports', 'technology']


# --- Caching functions ---
def cache_articles(category, country, articles):
    """
    Cache articles to a local file to reduce API calls

    Args:
        category (str): News category
        country (str): Country code
        articles (list): Articles to cache
    """
    try:
        cache_dir = os.path.join('assets', 'cache')
        os.makedirs(cache_dir, exist_ok=True)

        cache_file = os.path.join(cache_dir, f"news_{category}_{country}.json")
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'articles': articles
        }

        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
    except Exception as e:
        print(f"Error caching articles: {e}")


def get_cached_articles(category, country):
    """
    Get cached articles if available and not expired

    Args:
        category (str): News category
        country (str): Country code

    Returns:
        list: Cached articles or None if not available
    """
    try:
        cache_file = os.path.join('assets', 'cache', f"news_{category}_{country}.json")

        if not os.path.exists(cache_file):
            return None

        # Check if cache is less than 30 minutes old
        file_mod_time = os.path.getmtime(cache_file)
        if (datetime.now().timestamp() - file_mod_time) > (30 * 60):
            return None

        with open(cache_file, 'r') as f:
            cache_data = json.load(f)

        return cache_data.get('articles')
    except Exception as e:
        print(f"Error reading cache: {e}")
        return None


def get_sample_news():
    """Return sample news data when API fails"""
    return [
        {
            'title': 'Sample News Article 1',
            'description': 'This is a sample news article for testing purposes when the API is unavailable.',
            'url': 'https://example.com/news/1',
            'urlToImage': 'https://via.placeholder.com/150',
            'source': {'name': 'Sample News'},
            'publishedAt': datetime.now().isoformat()
        },
        {
            'title': 'Sample News Article 2',
            'description': 'Another sample news article for when the API is unavailable or rate limited.',
            'url': 'https://example.com/news/2',
            'urlToImage': 'https://via.placeholder.com/150',
            'source': {'name': 'Sample News'},
            'publishedAt': datetime.now().isoformat()
        },
        {
            'title': 'Technology Trends 2025',
            'description': 'A look at the biggest technology trends expected to shape the industry in 2025.',
            'url': 'https://example.com/news/3',
            'urlToImage': 'https://via.placeholder.com/150',
            'source': {'name': 'Sample Tech News'},
            'publishedAt': datetime.now().isoformat()
        }
    ]