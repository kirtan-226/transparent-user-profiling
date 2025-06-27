import requests
import json

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None

    def set_token(self, token):
        self.token = token

    def get_headers(self):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def register(self, username, email, password, categories=None):
        payload = {"username": username, "email": email, "password": password}
        if categories is not None:
            payload["categories"] = categories
        response = requests.post(
            f"{self.base_url}/auth/register",
            json=payload
        )
        return response

    def login(self, username, password):
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password}
        )
        return response

    def get_current_user(self):
        response = requests.get(
            f"{self.base_url}/auth/me",
            headers=self.get_headers()
        )
        return response

    def fetch_news(self, categories, keywords="", locations=None, limit=40):
        response = requests.post(
            f"{self.base_url}/news/fetch",
            json={"categories": categories, "keywords": keywords, "locations": locations, "limit": limit},
            headers=self.get_headers()
        )
        return response

    def get_categories(self):
        response = requests.get(f"{self.base_url}/news/categories")
        return response

    def get_preferences(self):
        response = requests.get(
            f"{self.base_url}/user/preferences",
            headers=self.get_headers()
        )
        return response

    def update_preferences(self, categories, keywords="", locations=None, share_read_time=False, experimental_opt_in=False):
        response = requests.put(
            f"{self.base_url}/user/preferences",
            json={
                "categories": categories,
                "keywords": keywords,
                "locations": locations or [],
                "share_read_time": share_read_time,
                "experimental_opt_in": experimental_opt_in
            },
            headers=self.get_headers()
        )
        return response

    def save_article(self, article_id):
        response = requests.post(
            f"{self.base_url}/user/save-article/{article_id}",
            headers=self.get_headers()
        )
        return response

    def like_article(self, article_id):
        response = requests.post(
            f"{self.base_url}/user/like-article/{article_id}",
            headers=self.get_headers()
        )
        return response

    def read_article(self, article_id):
        response = requests.post(
            f"{self.base_url}/user/read-article/{article_id}",
            headers=self.get_headers()
        )
        return response

    def get_saved_articles(self):
        response = requests.get(
            f"{self.base_url}/user/saved-articles",
            headers=self.get_headers()
        )
        return response

    def get_liked_articles(self):
        response = requests.get(
            f"{self.base_url}/user/liked-articles",
            headers=self.get_headers()
        )
        return response

    def get_personalized_news(self):
        response = requests.get(
            f"{self.base_url}/news/personalized",
            headers=self.get_headers()
        )
        return response

    def get_explore_news(self, limit=10):
        response = requests.get(
            f"{self.base_url}/news/explore?limit={limit}",
            headers=self.get_headers()
        )
        return response


def format_error_detail(error_data, default_msg):
    """Normalize error details from the backend."""
    detail = error_data.get("detail", default_msg)
    if isinstance(detail, list):
        detail = "; ".join(item.get("msg", str(item)) for item in detail)
    return detail