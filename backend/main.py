# backend/main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
import pymongo
from pymongo import MongoClient
import os
import requests
import uuid
from urllib.parse import quote_plus
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from dotenv import load_dotenv
from ai_model import analyze_activity

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="News Feed API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8050"],  # React and Dash
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
try:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    # Test the connection
    client.admin.command('ping')
    db = client.news_feed_db
    users_collection = db.users
    news_collection = db.news
    user_preferences_collection = db.user_preferences
    print("MongoDB connected successfully")
except Exception as e:
    print(f"MongoDB connection error: {e}")
    # You might want to exit here or handle this appropriately

# Configuration
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "758c48dbb96c4f96b40fd091e07070ac")
SECRET_KEY = os.getenv("SECRET_KEY", "vishnu16")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security
security = HTTPBearer()

# Pydantic models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    categories: Optional[List[str]] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserPreferences(BaseModel):
    categories: List[str]
    keywords: Optional[str] = ""
    locations: Optional[List[str]] = []
    share_read_time: Optional[bool] = False
    experimental_opt_in: Optional[bool] = False

class Article(BaseModel):
    article_id: str
    title: str
    description: str
    url: str
    urlToImage: Optional[str]
    publishedAt: str
    source: str
    category: str
    explanation: Optional[str] = ""

class NewsFilter(BaseModel):
    categories: Optional[List[str]] = ["general"]
    keywords: Optional[str] = ""
    locations: Optional[List[str]] = None
    limit: Optional[int] = 20

# Helper functions
def create_access_token(data: dict):
    to_encode = data.copy()
    # Fix: Use timezone-aware datetime
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        print(f"Verifying token: {credentials.credentials[:20]}...")  # Only print first 20 chars for security
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"Token payload: {payload}")
        user_id = payload.get("sub")
        print(f"User ID from token: {user_id}")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.PyJWTError as e:
        print(f"JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"Unexpected error in verify_token: {e}")
        raise HTTPException(status_code=401, detail="Token verification failed")

def get_user_by_id(user_id: str):
    print(f"Looking up user by ID: {user_id}")
    try:
        user = users_collection.find_one({"user_id": user_id})
        print(f"User lookup result: {type(user)}")
        if user:
            print(f"User found: {user.get('username', 'No username') if isinstance(user, dict) else 'User is not dict'}")
        else:
            print("No user found")
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Ensure user is a dictionary
        if not isinstance(user, dict):
            print(f"ERROR: User is not a dictionary, it's a {type(user)}: {user}")
            raise HTTPException(status_code=500, detail="Database returned invalid user data")
            
        return user
    except Exception as e:
        print(f"Error in get_user_by_id: {e}")
        raise

# Authentication endpoints
@app.post("/api/auth/register")
async def register_user(user: UserRegister):
    # Check if username exists
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email exists
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Create new user
    user_id = str(uuid.uuid4())
    new_user = {
        "user_id": user_id,
        "username": user.username,
        "email": user.email,
        "password": generate_password_hash(user.password),
        "created_at": datetime.now(),
        "saved_articles": [],
        "liked_articles": []
    }
    
    users_collection.insert_one(new_user)
    
    # Create default preferences
    default_preferences = {
        "user_id": user_id,
        "categories": user.categories if user.categories else ["general"],
        "keywords": "",
        "locations": [],
        "share_read_time": False,
        "experimental_opt_in": False,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    user_preferences_collection.insert_one(default_preferences)
    
    return {"message": "User registered successfully", "user_id": user_id}

@app.post("/api/auth/login")
async def login_user(user: UserLogin):
    # Find user
    user_data = users_collection.find_one({"username": user.username})
    if not user_data or not check_password_hash(user_data["password"], user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create access token
    access_token = create_access_token(data={"sub": user_data["user_id"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": user_data["user_id"],
            "username": user_data["username"],
            "email": user_data["email"]
        }
    }

# News endpoints
@app.post("/api/news/fetch")
async def fetch_news(filters: NewsFilter, user_id: str = Depends(verify_token)):
    news_articles = []
    
    for category in filters.categories:
        url = f"https://newsapi.org/v2/top-headlines?category={category}&apiKey={NEWS_API_KEY}"
        
        query_parts = []
        if filters.keywords:
            query_parts.append(filters.keywords)
        if filters.locations:
            query_parts.append(" OR ".join(filters.locations))
        if query_parts:
            url += "&q=" + quote_plus(" ".join(query_parts))
        
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes
            news_data = response.json()
            
            # Check if news_data is a dict and has the expected structure
            if not isinstance(news_data, dict):
                raise HTTPException(status_code=500, detail="Invalid response format from news API")
            
            if news_data.get("status") == "ok" and "articles" in news_data:
                articles = news_data.get("articles", [])
                if not isinstance(articles, list):
                    continue
                    
                for article in articles[:filters.limit//len(filters.categories)]:
                    # Ensure article is a dictionary
                    if not isinstance(article, dict):
                        continue
                        
                    # Store article in database
                    article_id = str(uuid.uuid4())
                    
                    # Safely get source information
                    source_info = article.get("source", {})
                    source_name = "Unknown"
                    if isinstance(source_info, dict):
                        source_name = source_info.get("name", "Unknown")
                    elif isinstance(source_info, str):
                        source_name = source_info
                    
                    article_data = {
                        "article_id": article_id,
                        "title": article.get("title", "No Title") if isinstance(article.get("title"), str) else "No Title",
                        "description": article.get("description", "No Description") if isinstance(article.get("description"), str) else "No Description",
                        "url": article.get("url", "#") if isinstance(article.get("url"), str) else "#",
                        "urlToImage": article.get("urlToImage", "") if isinstance(article.get("urlToImage"), str) else "",
                        "publishedAt": article.get("publishedAt", "") if isinstance(article.get("publishedAt"), str) else "",
                        "source": source_name,
                        "category": category,
                        "explanation": f"Matched category '{category}'" + (f" and keywords '{filters.keywords}'" if filters.keywords else ""),
                        "created_at": datetime.now()
                    }
                    
                    # Check if article already exists
                    existing = news_collection.find_one({"title": article_data["title"]})
                    if not existing:
                        news_collection.insert_one(article_data)
                    else:
                        article_id = existing["article_id"]
                        article_data["article_id"] = article_id
                    
                    news_articles.append(article_data)
            else:
                print(f"API Error for category {category}: {news_data.get('message', 'Unknown error')}")
                    
        except requests.RequestException as e:
            print(f"Request error for category {category}: {str(e)}")
            continue
        except Exception as e:
            print(f"Error fetching news for category {category}: {str(e)}")
            continue
    
    return {"articles": news_articles}

@app.get("/api/news/categories")
async def get_news_categories():
    categories = ["business", "entertainment", "general", "health", "science", "sports", "technology"]
    return {"categories": categories}

def _fetch_trending_news(limit: int = 10):
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
    news_articles = []
    try:
        response = requests.get(url)
        response.raise_for_status()
        news_data = response.json()
        if news_data.get("status") == "ok" and "articles" in news_data:
            articles = news_data.get("articles", [])
            for article in articles[:limit]:
                if not isinstance(article, dict):
                    continue
                article_id = str(uuid.uuid4())
                source_info = article.get("source", {})
                source_name = source_info.get("name", "Unknown") if isinstance(source_info, dict) else source_info
                article_data = {
                    "article_id": article_id,
                    "title": article.get("title", "No Title"),
                    "description": article.get("description", "No Description"),
                    "url": article.get("url", "#"),
                    "urlToImage": article.get("urlToImage", ""),
                    "publishedAt": article.get("publishedAt", ""),
                    "source": source_name,
                    "category": "explore",
                    "explanation": "Trending article",
                    "created_at": datetime.now()
                }
                existing = news_collection.find_one({"title": article_data["title"]})
                if not existing:
                    news_collection.insert_one(article_data)
                else:
                    article_id = existing["article_id"]
                    article_data["article_id"] = article_id
                news_articles.append(article_data)
    except Exception as e:
        print(f"Error fetching trending news: {e}")
    return news_articles


@app.get("/api/news/explore")
async def get_explore_news(limit: int = 10):
    articles = _fetch_trending_news(limit)
    return {"articles": articles}

# New endpoint: personalized news feed using simple activity analysis
@app.get("/api/news/personalized")
async def get_personalized_news(user_id: str = Depends(verify_token)):
    # Retrieve user preferences
    preferences = user_preferences_collection.find_one({"user_id": user_id}) or {
        "categories": ["general"],
        "keywords": ""
    }

    # Gather saved articles for activity analysis
    user = get_user_by_id(user_id)
    liked_ids = user.get("liked_articles", []) if isinstance(user, dict) else []
    liked_articles = []
    for aid in liked_ids:
        article = news_collection.find_one({"article_id": aid})
        if article:
            liked_articles.append(article)

    # Determine recommended categories
    rec_data = analyze_activity(liked_articles, preferences)
    rec_categories = rec_data["categories"]
    rec_locations = rec_data["locations"]

    filters = NewsFilter(
        categories=rec_categories,
        keywords=preferences.get("keywords", ""),
        locations=rec_locations,
        limit=20,
    )
    result = await fetch_news(filters, user_id)
    for article in result.get("articles", []):
        article["explanation"] += " | Recommended based on your activity"
        if rec_locations:
            article["explanation"] += f" | Locations: {', '.join(rec_locations)}"

    if preferences.get("experimental_opt_in"):
        trending = _fetch_trending_news(5)
        for article in trending:
            article["explanation"] += " | Explore recommendation"
        result["articles"].extend(trending)

    return result


# User preferences endpoints
@app.get("/api/user/preferences")
async def get_user_preferences(user_id: str = Depends(verify_token)):
    preferences = user_preferences_collection.find_one({"user_id": user_id})
    if not preferences:
        # Create default preferences
        default_preferences = {
            "user_id": user_id,
            "categories": ["general"],
            "keywords": "",
            "locations": [],
            "share_read_time": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        user_preferences_collection.insert_one(default_preferences)
        return default_preferences
    
    # Remove MongoDB's _id field for JSON serialization
    if "_id" in preferences:
        del preferences["_id"]
    
    if "locations" not in preferences:
        preferences["locations"] = []
    if "share_read_time" not in preferences:
        preferences["share_read_time"] = False
    if "experimental_opt_in" not in preferences:
        preferences["experimental_opt_in"] = False

    return preferences

@app.put("/api/user/preferences")
async def update_user_preferences(preferences: UserPreferences, user_id: str = Depends(verify_token)):
    user_preferences_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "categories": preferences.categories,
            "keywords": preferences.keywords,
            "locations": preferences.locations,
            "share_read_time": preferences.share_read_time,
            "experimental_opt_in": preferences.experimental_opt_in,
            "updated_at": datetime.now()
        }},
        upsert=True
    )
    return {"message": "Preferences updated successfully"}

# Saved articles endpoints
@app.post("/api/user/save-article/{article_id}")
async def save_article(article_id: str, user_id: str = Depends(verify_token)):
    # Check if article exists
    article = news_collection.find_one({"article_id": article_id})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Add to user's saved articles
    users_collection.update_one(
        {"user_id": user_id},
        {"$addToSet": {"saved_articles": article_id}}
    )
    
    return {"message": "Article saved successfully"}

    # Like articles endpoints
@app.post("/api/user/like-article/{article_id}")
async def like_article(article_id: str, user_id: str = Depends(verify_token)):
    article = news_collection.find_one({"article_id": article_id})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    users_collection.update_one(
        {"user_id": user_id},
        {"$addToSet": {"liked_articles": article_id}}
    )
    return {"message": "Article liked"}

@app.get("/api/user/liked-articles")
async def get_liked_articles(user_id: str = Depends(verify_token)):
    user = get_user_by_id(user_id)
    liked_ids = user.get("liked_articles", []) if isinstance(user, dict) else []
    liked_articles = []
    for aid in liked_ids:
        article = news_collection.find_one({"article_id": aid})
        if article:
            if "_id" in article:
                del article["_id"]
            liked_articles.append(article)
    return {"liked_articles": liked_articles}


@app.get("/api/user/saved-articles")
async def get_saved_articles(user_id: str = Depends(verify_token)):
    try:
        user = get_user_by_id(user_id)
        
        # Debug: Print user data structure
        print(f"User data type: {type(user)}")
        print(f"User data: {user}")
        
        # Ensure user is a dictionary
        if not isinstance(user, dict):
            print(f"ERROR: User is not a dictionary: {type(user)}")
            return {"saved_articles": []}
        
        saved_article_ids = user.get("saved_articles", [])
        print(f"Saved article IDs: {saved_article_ids}, type: {type(saved_article_ids)}")
        
        # Ensure saved_article_ids is a list
        if not isinstance(saved_article_ids, list):
            print(f"Warning: saved_article_ids is not a list: {type(saved_article_ids)}")
            saved_article_ids = []
        
        saved_articles = []
        for article_id in saved_article_ids:
            print(f"Looking for article: {article_id}")
            article = news_collection.find_one({"article_id": article_id})
            if article:
                # Remove MongoDB's _id field for JSON serialization
                if "_id" in article:
                    del article["_id"]  
                saved_articles.append(article)
                print(f"Added article: {article.get('title', 'No title')}")
        
        print(f"Returning {len(saved_articles)} saved articles")
        return {"saved_articles": saved_articles}
        
    except Exception as e:
        print(f"Error in get_saved_articles: {e}")
        return {"saved_articles": [], "error": str(e)}

@app.delete("/api/user/saved-articles/{article_id}")
async def remove_saved_article(article_id: str, user_id: str = Depends(verify_token)):
    users_collection.update_one(
        {"user_id": user_id},
        {"$pull": {"saved_articles": article_id}}
    )
    return {"message": "Article removed from saved"}

# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)