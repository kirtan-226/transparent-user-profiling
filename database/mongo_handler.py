from pymongo import MongoClient
from datetime import datetime

def connect_db():
    client = MongoClient("mongodb://localhost:27017/")
    return client['hcai_news']

def log_login(username):
    db = connect_db()
    db.sessions.insert_one({"user": username, "login_time": datetime.now()})
