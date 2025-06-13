# frontend/app.py
import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

# Initialize the Dash app
app = dash.Dash(__name__,
                external_stylesheets=[dbc.themes.BOOTSTRAP],
                suppress_callback_exceptions=True)

server = app.server

# Helper functions for API calls
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
    
    def fetch_news(self, categories, keywords="", locations=None, limit=20):
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
    
    def get_saved_articles(self):
        response = requests.get(
            f"{self.base_url}/user/saved-articles",
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

# Initialize API client
api_client = APIClient(API_BASE_URL)

# App layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='auth-store', storage_type='session'),
    html.Div(id='page-content')
])

# Layout components
def create_login_layout():
    return dbc.Container([
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

def create_register_layout():
    return dbc.Container([
        html.H1("News Feed App - Register", className="text-center mt-4 mb-4"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    html.Div("Create an Account", className="card-header"),
                    dbc.CardBody([
                        dbc.Input(id="register-username", placeholder="Username", type="text", className="mb-3"),
                        dbc.Input(id="register-email", placeholder="Email", type="email", className="mb-3"),
                        dbc.Input(id="register-password", placeholder="Password", type="password", className="mb-3"),
                        dbc.Input(id="register-confirm-password", placeholder="Confirm Password", type="password", className="mb-3"),
                        html.H6("Select Topics of Interest"),
                        dbc.Checklist(
                            id="register-categories",
                            options=[
                                {"label": "Business", "value": "business"},
                                {"label": "Entertainment", "value": "entertainment"},
                                {"label": "General", "value": "general"},
                                {"label": "Health", "value": "health"},
                                {"label": "Science", "value": "science"},
                                {"label": "Sports", "value": "sports"},
                                {"label": "Technology", "value": "technology"}
                            ],
                            value=["general"],
                            inline=True,
                            className="mb-3"
                        ),
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

def create_news_feed_layout():
    return dbc.Container([
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
                            options=["business", "entertainment", "general", "health", "science", "sports", "technology"],
                            value=["general"],
                            inline=True
                        ),
                        html.Hr(),
                        html.H6("Search"),
                        dbc.Input(id="search-keywords", placeholder="Search keywords", type="text", className="mb-3"),
                        html.H6("Preferred Locations"),
                        dbc.Checklist(
                            id="location-preferences",
                            options=[
                                {"label": loc, "value": loc} for loc in ["USA", "China", "India", "Russia", "UK"]
                            ],
                            value=[],
                            inline=True,
                            className="mb-3"
                        ),
                        html.H6("Data Sharing"),
                        dbc.Checklist(
                            id="data-consent-toggle",
                            options=[
                                {"label": "Share Reading Time", "value": "read_time"},
                                {"label": "Explore New Content", "value": "experimental"}
                            ],
                            value=[],
                            switch=True,
                            className="mb-3"
                        ),
                        dbc.Button("Apply Filters", id="apply-filters", color="primary", className="w-100"),
                        html.Hr(),
                        html.H6("Save Preferences"),
                        dbc.Button("Save Current Preferences", id="save-preferences", color="success", className="w-100 mb-2"),
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
            ], width=9)
        ])
    ], fluid=True)

def create_news_card(article):
    return dbc.Card([
        dbc.CardImg(
            src=article.get("urlToImage") if article.get("urlToImage") else "https://via.placeholder.com/300x200?text=No+Image",
            top=True
        ),
        dbc.CardBody([
            html.H5(article["title"], className="card-title"),
            html.P(article["description"], className="card-text"),
            html.P([
                html.Small(f"Source: {article['source']} | Category: {article['category'].capitalize()}",
                          className="text-muted")
            ]),
            html.Small(article.get("explanation", ""), className="text-muted d-block mb-2"),
            dbc.Button("Read More", href=article["url"], target="_blank", color="primary", className="me-2"),
            dbc.Button("Save Article", id={"type": "save-article-btn", "index": article["article_id"]},
                      color="success", className="me-2"),
            dbc.Button("Like", id={"type": "like-article-btn", "index": article["article_id"]},
                      color="danger")
        ])
    ], className="mb-4 shadow-sm")

# Callbacks

@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')],
    [State('auth-store', 'data')]
)
def display_page(pathname, auth_data):
    if pathname == '/register':
        return create_register_layout()
    elif pathname == '/news-feed':
        if auth_data and auth_data.get('token'):
            api_client.set_token(auth_data['token'])
            return create_news_feed_layout()
        else:
            return create_login_layout()
    else:
        return create_login_layout()

@app.callback(
    [Output('register-error', 'children'),
     Output('register-success', 'children'),
     Output('url', 'pathname')],
    [Input('register-button', 'n_clicks')],
    [State('register-username', 'value'),
     State('register-email', 'value'),
     State('register-password', 'value'),
     State('register-confirm-password', 'value'),
     State('register-categories', 'value')],
    prevent_initial_call=True
)
def register_user(n_clicks, username, email, password, confirm_password, categories):
    if n_clicks is None:
        return "", "", dash.no_update

    if not username or not email or not password:
        return "All fields are required.", "", dash.no_update

    if password != confirm_password:
        return "Passwords do not match.", "", dash.no_update

    try:
        response = api_client.register(username, email, password, categories)
        if response.status_code == 200:
            return "", "Registration successful! Please login.", "/login"
        else:
            error_data = response.json()
            return error_data.get("detail", "Registration failed"), "", dash.no_update
    except Exception as e:
        return f"Connection error: {str(e)}", "", dash.no_update

@app.callback(
    [Output('login-error', 'children'),
     Output('url', 'pathname', allow_duplicate=True),
     Output('auth-store', 'data')],
    [Input('login-button', 'n_clicks')],
    [State('login-username', 'value'),
     State('login-password', 'value')],
    prevent_initial_call=True
)
def login_user(n_clicks, username, password):
    if n_clicks is None:
        return "", dash.no_update, dash.no_update

    if not username or not password:
        return "Username and password are required.", dash.no_update, dash.no_update

    try:
        response = api_client.login(username, password)
        if response.status_code == 200:
            data = response.json()
            auth_data = {
                'token': data['access_token'],
                'user': data['user']
            }
            api_client.set_token(data['access_token'])
            return "", "/news-feed", auth_data
        else:
            error_data = response.json()
            return error_data.get("detail", "Login failed"), dash.no_update, dash.no_update
    except Exception as e:
        return f"Connection error: {str(e)}", dash.no_update, dash.no_update

@app.callback(
    [Output('url', 'pathname', allow_duplicate=True),
     Output('auth-store', 'clear_data')],
    [Input('logout-button', 'n_clicks')],
    prevent_initial_call=True
)
def logout_user(n_clicks):
    if n_clicks:
        api_client.set_token(None)
        return "/login", True
    return dash.no_update, dash.no_update

@app.callback(
    Output('category-filter', 'options'),
    [Input('url', 'pathname')],
    [State('auth-store', 'data')]
)
def load_categories(pathname, auth_data):
    if pathname == '/news-feed' and auth_data and auth_data.get('token'):
        try:
            response = api_client.get_categories()
            if response.status_code == 200:
                categories = response.json()                
                if 'categories' in categories:
                    category_list = categories['categories']
                    return [{'label': cat.title(), 'value': cat} for cat in category_list]
                else:
                    return ["business", "entertainment", "general", "health", "science", "sports", "technology"]
        except Exception as e:
            print(f"Error loading categories: {e}")
            return ["business", "entertainment", "general", "health", "science", "sports", "technology"]
    
    
    return ["business", "entertainment", "general", "health", "science", "sports", "technology"]
    
    # Default categories
    return [
        {"label": "General", "value": "general"},
        {"label": "Business", "value": "business"},
        {"label": "Technology", "value": "technology"},
        {"label": "Sports", "value": "sports"},
        {"label": "Health", "value": "health"},
        {"label": "Science", "value": "science"}
    ]

@app.callback(
    Output('news-feed-container', 'children'),
    [Input('apply-filters', 'n_clicks'),
     Input('url', 'pathname')],
    [State('category-filter', 'value'),
     State('search-keywords', 'value'),
     State('location-preferences', 'value'),
     State('auth-store', 'data')],
    prevent_initial_call=False
)
def update_news_feed(n_clicks, pathname, categories, keywords, locations, auth_data):
    if pathname != '/news-feed' or not auth_data or not auth_data.get('token'):
        return []

    try:
        api_client.set_token(auth_data['token'])
        categories = categories or ["general"]
        keywords = keywords or ""
        
        if n_clicks is None:
            response = api_client.get_personalized_news()
        else:
            response = api_client.fetch_news(categories, keywords, locations or [])
        if response.status_code == 200:
            data = response.json()  # This returns {"articles": [...]}
            articles = data.get('articles', [])  # Extract the articles array
            if articles:
                return [create_news_card(article) for article in articles]
            else:
                return [html.Div("No articles found.", className="text-center text-muted")]
        else:
            error_msg = f"Error loading news (Status: {response.status_code})"
            print(f"API Error: {response.text}")
            return [html.Div(error_msg, className="text-center text-danger")]
    except Exception as e:
        print(f"Exception in update_news_feed: {str(e)}")
        return [html.Div(f"Connection error: {str(e)}", className="text-center text-danger")] 

@app.callback(
    Output('user-welcome', 'children'),
    [Input('url', 'pathname')],
    [State('auth-store', 'data')]
)
def update_user_welcome(pathname, auth_data):
    if pathname == '/news-feed' and auth_data and auth_data.get('user'):
        return f"Welcome, {auth_data['user']['username']}!"
    return ""

@app.callback(
    Output('save-preferences-status', 'children'),
    [Input('save-preferences', 'n_clicks')],
    [State('category-filter', 'value'),
     State('search-keywords', 'value'),
     State('location-preferences', 'value'),
     State('data-consent-toggle', 'value'),
     State('auth-store', 'data')],
    prevent_initial_call=True
)
def save_user_preferences(n_clicks, categories, keywords, locations, data_toggle, auth_data):
    if n_clicks and auth_data and auth_data.get('token'):
        try:
            api_client.set_token(auth_data['token'])
            share_read_time = 'read_time' in (data_toggle or [])
            response = api_client.update_preferences(
                categories or [],
                keywords or "",
                locations or [],
                share_read_time=share_read_time,
                experimental_opt_in='experimental' in (data_toggle or [])
            )
            if response.status_code == 200:
                return dbc.Alert("Preferences saved successfully!", color="success", duration=3000)
            else:
                return dbc.Alert("Failed to save preferences.", color="danger", duration=3000)
        except Exception as e:
            return dbc.Alert(f"Error: {str(e)}", color="danger", duration=3000)
    return ""

@app.callback(
    Output('saved-articles-list', 'children'),
    [Input('refresh-saved', 'n_clicks'),
     Input('url', 'pathname')],
    [State('auth-store', 'data')],
    prevent_initial_call=False
)
def load_saved_articles(n_clicks, pathname, auth_data):
    if pathname == '/news-feed' and auth_data and auth_data.get('token'):
        try:
            api_client.set_token(auth_data['token'])
            response = api_client.get_saved_articles()
            if response.status_code == 200:
                data = response.json()  # This returns {"saved_articles": [...]}
                articles = data.get('saved_articles', [])  # Extract the saved_articles array
                if articles:
                    return [
                        html.Div([
                            html.A(article['title'], href=article['url'], target="_blank", 
                                  className="text-decoration-none"),
                            html.Br(),
                            html.Small(article['source'], className="text-muted")
                        ], className="mb-2") for article in articles
                    ]
                else:
                    return [html.P("No saved articles.", className="text-muted")]
            else:
                print(f"Saved articles API error: {response.status_code} - {response.text}")
                return [html.P("Error loading saved articles.", className="text-danger")]
        except Exception as e:
            print(f"Exception in load_saved_articles: {str(e)}")
            return [html.P(f"Error loading saved articles: {str(e)}", className="text-danger")]
    return []

@app.callback(
    Output({'type': 'save-article-btn', 'index': dash.dependencies.MATCH}, 'children'),
    [Input({'type': 'save-article-btn', 'index': dash.dependencies.MATCH}, 'n_clicks')],
    [State('auth-store', 'data')],
    prevent_initial_call=True
)
def save_article(n_clicks, auth_data):
    if n_clicks and auth_data and auth_data.get('token'):
        try:
            ctx = callback_context
            if ctx.triggered:
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]
                article_id = json.loads(button_id)['index']
                
                api_client.set_token(auth_data['token'])
                response = api_client.save_article(article_id)
                if response.status_code == 200:
                    return "Saved!"
                else:
                    return "Save Failed"
        except Exception as e:
            return "Error"
    return "Save Article"

@app.callback(
    Output({'type': 'like-article-btn', 'index': dash.dependencies.MATCH}, 'children'),
    [Input({'type': 'like-article-btn', 'index': dash.dependencies.MATCH}, 'n_clicks')],
    [State('auth-store', 'data')],
    prevent_initial_call=True
)
def like_article(n_clicks, auth_data):
    if n_clicks and auth_data and auth_data.get('token'):
        try:
            ctx = callback_context
            if ctx.triggered:
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]
                article_id = json.loads(button_id)['index']
                api_client.set_token(auth_data['token'])
                response = api_client.like_article(article_id)
                if response.status_code == 200:
                    return "Liked!"
                else:
                    return "Like Failed"
        except Exception:
            return "Error"
    return "Like"

if __name__ == '__main__':
    app.run(debug=True, port=8050)