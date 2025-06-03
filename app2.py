import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
import pymongo
from pymongo import MongoClient
import pandas as pd
import os
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize MongoDB connection
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(mongo_uri)
db = client.news_feed_db
users_collection = db.users
news_collection = db.news
user_preferences_collection = db.user_preferences

# News API key
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "758c48dbb96c4f96b40fd091e07070ac")

# Initialize the Dash app with Bootstrap
app = dash.Dash(__name__,
                external_stylesheets=[dbc.themes.BOOTSTRAP],
                suppress_callback_exceptions=True)
server = app.server

# Set a secret key for Flask sessions
server.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "vishnu16")
)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(server)

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, username, email, user_id):
        self.id = user_id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    user_data = users_collection.find_one({"user_id": user_id})
    if user_data:
        return User(
            username=user_data["username"],
            email=user_data["email"],
            user_id=user_data["user_id"]
        )
    return None

# App layout with multiple pages
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])



# App layout with multiple pages
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# Layout for login page
login_layout = dbc.Container([
    html.H1("News Feed App - Login", className="text-center mt-4 mb-4"),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                html.Div("Login", className="card-header"),
                dbc.CardBody([
                    dbc.Input(id="login-username", placeholder="Username", type="text", className="mb-3"),
                    dbc.Input(id="login-password", placeholder="Password", type="password", className="mb-3"),
                    dbc.Button("Login", id="login-button", color="primary", className="mt-2 w-100"),
                    html.Div(id="login-error", className="text-danger mt-3"),
                    html.Hr(),
                    html.P("Don't have an account?"),
                    dbc.Button("Register", id="go-to-register", href="/register", color="secondary", className="w-100")
                ])
            ], className="shadow")
        ], width={"size": 6, "offset": 3})
    ])
], fluid=True)

# Layout for registration page
register_layout = dbc.Container([
    html.H1("News Feed App - Register", className="text-center mt-4 mb-4"),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                html.Div("Create an Account", className="card-header"),
                dbc.CardBody([
                    dbc.Input(id="register-username", placeholder="Username", type="text", className="mb-3"),
                    dbc.Input(id="register-email", placeholder="Email", type="email", className="mb-3"),
                    dbc.Input(id="register-password", placeholder="Password", type="password", className="mb-3"),
                    dbc.Input(id="register-confirm-password", placeholder="Confirm Password", type="password",
                              className="mb-3"),
                    dbc.Button("Register", id="register-button", color="primary", className="mt-2 w-100"),
                    html.Div(id="register-error", className="text-danger mt-3"),
                    html.Div(id="register-success", className="text-success mt-3"),
                    html.Hr(),
                    html.P("Already have an account?"),
                    dbc.Button("Login", id="go-to-login", href="/login", color="secondary", className="w-100")
                ])
            ], className="shadow")
        ], width={"size": 6, "offset": 3})
    ])
], fluid=True)


# Layout for the main news feed page
def create_news_feed_layout():
    # Categories for news filtering
    categories = ["business", "entertainment", "general", "health", "science", "sports", "technology"]

    return dbc.Container([
        dcc.Store(id='user-data-store'),

        # Navbar
        dbc.Navbar([
            dbc.Container([
                dbc.NavbarBrand("News Feed App", className="ms-2"),
                dbc.NavbarToggler(id="navbar-toggler"),
                dbc.Collapse([
                    dbc.Nav([
                        dbc.NavItem(html.Div(id="user-welcome", className="nav-link")),
                        dbc.NavItem(dbc.Button("Logout", id="logout-button", color="light", className="ms-2"))
                    ], className="ms-auto")
                ], id="navbar-collapse", navbar=True)
            ])
        ], color="dark", dark=True, className="mb-4"),

        # Main content
        dbc.Row([
            # Sidebar for filters
            dbc.Col([
                dbc.Card([
                    html.Div("News Preferences", className="card-header"),
                    dbc.CardBody([
                        html.H6("Categories"),
                        dbc.Checklist(
                            id="category-filter",
                            options=[{"label": cat.capitalize(), "value": cat} for cat in categories],
                            value=["general"],
                            inline=True
                        ),
                        html.Hr(),
                        html.H6("Search"),
                        dbc.Input(id="search-keywords", placeholder="Search keywords", type="text", className="mb-3"),
                        dbc.Button("Apply Filters", id="apply-filters", color="primary", className="w-100"),
                        html.Hr(),
                        html.H6("Save Preferences"),
                        dbc.Button("Save Current Preferences", id="save-preferences", color="success",
                                   className="w-100 mb-2"),
                        html.Div(id="save-preferences-status")
                    ])
                ], className="shadow-sm mb-4"),

                dbc.Card([
                    html.Div("Saved Articles", className="card-header"),
                    dbc.CardBody([
                        html.Div(id="saved-articles-list"),
                        dbc.Button("Refresh Saved Articles", id="refresh-saved", color="info", className="w-100 mt-3")
                    ])
                ], className="shadow-sm")
            ], width=3),

            # Main news feed
            dbc.Col([
                html.H4("Latest News", className="mb-4"),
                html.Div(id="news-feed-container", children=[
                    dbc.Spinner(color="primary", type="grow", fullscreen=False)
                ]),
                html.Div(id="load-more-container", className="text-center mt-4", children=[
                    dbc.Button("Load More", id="load-more", color="secondary")
                ])
            ], width=9)
        ])
    ], fluid=True)


# Callback to handle URL routing
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == '/register':
        return register_layout
    elif pathname == '/news-feed':
        if current_user.is_authenticated:
            return create_news_feed_layout()
        else:
            return login_layout
    else:
        return login_layout


# Callback for user registration
@app.callback(
    [Output('register-error', 'children'),
     Output('register-success', 'children'),
     Output('url', 'pathname')],
    [Input('register-button', 'n_clicks')],
    [State('register-username', 'value'),
     State('register-email', 'value'),
     State('register-password', 'value'),
     State('register-confirm-password', 'value')],
    prevent_initial_call=True
)
def register_user(n_clicks, username, email, password, confirm_password):
    if n_clicks is None:
        return "", "", dash.no_update

    # Basic validation
    if not username or not email or not password:
        return "All fields are required.", "", dash.no_update

    if password != confirm_password:
        return "Passwords do not match.", "", dash.no_update

    # Check if username already exists
    if users_collection.find_one({"username": username}):
        return f"Username '{username}' is already taken.", "", dash.no_update

    # Check if email already exists
    if users_collection.find_one({"email": email}):
        return f"Email '{email}' is already registered.", "", dash.no_update

    # Create a new user
    user_id = str(uuid.uuid4())
    new_user = {
        "user_id": user_id,
        "username": username,
        "email": email,
        "password": generate_password_hash(password),
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

    # Success message and redirect to login
    return "", "Registration successful! Please login.", "/login"


# Callback for user login
@app.callback(
    [Output('login-error', 'children'),
     Output('url', 'pathname', allow_duplicate=True)],
    [Input('login-button', 'n_clicks')],
    [State('login-username', 'value'),
     State('login-password', 'value')],
    prevent_initial_call=True
)
def login_user_callback(n_clicks, username, password):
    if n_clicks is None:
        return "", dash.no_update

    # Basic validation
    if not username or not password:
        return "Username and password are required.", dash.no_update

    # Check if user exists
    user_data = users_collection.find_one({"username": username})
    if not user_data:
        return "Invalid username or password.", dash.no_update

    # Check password
    if not check_password_hash(user_data["password"], password):
        return "Invalid username or password.", dash.no_update

    # Login user
    user = User(
        username=user_data["username"],
        email=user_data["email"],
        user_id=user_data["user_id"]
    )
    login_user(user)

    # Redirect to news feed
    return "", "/news-feed"


# Callback for logout
@app.callback(
    Output('url', 'pathname', allow_duplicate=True),
    [Input('logout-button', 'n_clicks')],
    prevent_initial_call=True
)
def logout_user_callback(n_clicks):
    if n_clicks is None:
        return dash.no_update

    logout_user()
    return "/login"


# Callback to populate user welcome message
@app.callback(
    Output('user-welcome', 'children'),
    [Input('user-data-store', 'data')]
)
def update_welcome_message(data):
    if current_user.is_authenticated:
        return f"Welcome, {current_user.username}!"
    return ""


# Callback to fetch and display news
@app.callback(
    Output('news-feed-container', 'children'),
    [Input('apply-filters', 'n_clicks'),
     Input('url', 'pathname')],
    [State('category-filter', 'value'),
     State('search-keywords', 'value')],
    prevent_initial_call=True
)
def update_news_feed(n_clicks, pathname, categories, keywords):
    if not current_user.is_authenticated or pathname != "/news-feed":
        return []

    if not categories:
        categories = ["general"]

    news_cards = []

    # Fetch news for each selected category
    for category in categories:
        # Build the API URL
        url = f"https://newsapi.org/v2/top-headlines?category={category}&apiKey={NEWS_API_KEY}"

        if keywords:
            url += f"&q={keywords}"

        try:
            response = requests.get(url)
            news_data = response.json()

            if news_data["status"] == "ok":
                for article in news_data["articles"][:10]:  # Limit to 10 articles per category
                    # Store article in database
                    article_id = str(uuid.uuid4())
                    article_data = {
                        "article_id": article_id,
                        "title": article.get("title", "No Title"),
                        "description": article.get("description", "No Description"),
                        "url": article.get("url", "#"),
                        "urlToImage": article.get("urlToImage", ""),
                        "publishedAt": article.get("publishedAt", ""),
                        "source": article.get("source", {}).get("name", "Unknown"),
                        "category": category,
                        "created_at": datetime.now()
                    }

                    # Check if article already exists
                    existing = news_collection.find_one({"title": article_data["title"]})
                    if not existing:
                        news_collection.insert_one(article_data)
                    else:
                        article_id = existing["article_id"]

                    # Create card for the article
                    card = dbc.Card([
                        dbc.CardImg(src=article_data["urlToImage"] if article_data[
                            "urlToImage"] else "https://via.placeholder.com/300x200?text=No+Image", top=True),
                        dbc.CardBody([
                            html.H5(article_data["title"], className="card-title"),
                            html.P(article_data["description"], className="card-text"),
                            html.P([
                                html.Small(f"Source: {article_data['source']} | Category: {category.capitalize()}",
                                           className="text-muted")
                            ]),
                            dbc.Button("Read More", href=article_data["url"], target="_blank", color="primary",
                                       className="me-2"),
                            dbc.Button("Save Article", id={"type": "save-article-btn", "index": article_id},
                                       color="success")
                        ])
                    ], className="mb-4 shadow-sm")

                    news_cards.append(card)

        except Exception as e:
            news_cards.append(html.Div(f"Error fetching news for {category}: {str(e)}"))

    if not news_cards:
        return html.Div("No news articles found. Try different filters.")

    return news_cards


# Callback to save user preferences
@app.callback(
    Output('save-preferences-status', 'children'),
    [Input('save-preferences', 'n_clicks')],
    [State('category-filter', 'value'),
     State('search-keywords', 'value')]
)
def save_user_preferences(n_clicks, categories, keywords):
    if n_clicks is None or not current_user.is_authenticated:
        return ""

    if not categories:
        categories = ["general"]

    # Update preferences
    user_preferences_collection.update_one(
        {"user_id": current_user.id},
        {"$set": {
            "categories": categories,
            "keywords": keywords if keywords else "",
            "updated_at": datetime.now()
        }},
        upsert=True
    )

    return html.Div("Preferences saved successfully!", className="text-success mt-2")


# Callback for saving articles
@app.callback(
    Output('saved-articles-list', 'children'),
    [Input({'type': 'save-article-btn', 'index': dash.dependencies.ALL}, 'n_clicks'),
     Input('refresh-saved', 'n_clicks'),
     Input('url', 'pathname')]
)
def handle_saved_articles(save_clicks, refresh_clicks, pathname):
    if not current_user.is_authenticated:
        return html.Div("Please login to see saved articles.")

    # Check if a save button was clicked
    ctx = callback_context
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # If a save button was clicked
        if '{' in trigger_id:
            trigger_dict = eval(trigger_id)
            if trigger_dict['type'] == 'save-article-btn':
                article_id = trigger_dict['index']

                # Get article data
                article = news_collection.find_one({"article_id": article_id})
                if article:
                    # Update user's saved articles
                    users_collection.update_one(
                        {"user_id": current_user.id},
                        {"$addToSet": {"saved_articles": article_id}}
                    )

    # Get user data with saved articles
    user_data = users_collection.find_one({"user_id": current_user.id})
    if not user_data or "saved_articles" not in user_data or not user_data["saved_articles"]:
        return html.Div("No saved articles yet.")

    # Get saved articles
    saved_articles = []
    for article_id in user_data["saved_articles"]:
        article = news_collection.find_one({"article_id": article_id})
        if article:
            saved_articles.append(article)

    # Create list of saved articles
    saved_list = []
    for article in saved_articles:
        saved_list.append(
            dbc.ListGroupItem([
                html.Div([
                    html.A(article["title"], href=article["url"], target="_blank"),
                    html.Small(f"Source: {article['source']} | Category: {article['category'].capitalize()}",
                               className="d-block text-muted")
                ])
            ])
        )

    if not saved_list:
        return html.Div("No saved articles found.")

    return dbc.ListGroup(saved_list)


# Run the app
if __name__ == '__main__':
    app.run(debug=True)