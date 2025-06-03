# backend/main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import pymongo
from pymongo import MongoClient
import os
import requests
import uuid
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from dotenv import load_dotenv

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

class UserLogin(BaseModel):
    username: str
    password: str

class UserPreferences(BaseModel):
    categories: List[str]
    keywords: Optional[str] = ""

class Article(BaseModel):
    article_id: str
    title: str
    description: str
    url: str
    urlToImage: Optional[str]
    publishedAt: str
    source: str
    category: str

class NewsFilter(BaseModel):
    categories: Optional[List[str]] = ["general"]
    keywords: Optional[str] = ""
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
        "saved_articles": []
    }
    
    users_collection.insert_one(new_user)
    
    # Create default preferences
    default_preferences = {
        "user_id": user_id,
        "categories": ["general"],
        "keywords": "",
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

@app.get("/api/auth/me")
async def get_current_user(user_id: str = Depends(verify_token)):
    user = get_user_by_id(user_id)
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "email": user["email"]
    }

# News endpoints
@app.post("/api/news/fetch")
async def fetch_news(filters: NewsFilter, user_id: str = Depends(verify_token)):
    news_articles = []
    
    for category in filters.categories:
        url = f"https://newsapi.org/v2/top-headlines?category={category}&apiKey={NEWS_API_KEY}"
        
        if filters.keywords:
            url += f"&q={filters.keywords}"
        
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
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        user_preferences_collection.insert_one(default_preferences)
        return default_preferences
    
    # Remove MongoDB's _id field for JSON serialization
    if "_id" in preferences:
        del preferences["_id"]
    
    return preferences

@app.put("/api/user/preferences")
async def update_user_preferences(preferences: UserPreferences, user_id: str = Depends(verify_token)):
    user_preferences_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "categories": preferences.categories,
            "keywords": preferences.keywords,
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