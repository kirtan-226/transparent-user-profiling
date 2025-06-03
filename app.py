import dash
from dash import dcc, html, Input, Output, State, callback
import flask
import os
import requests
from pymongo import MongoClient
from datetime import datetime
import pandas as pd

# Initialize Flask server
server = flask.Flask(__name__)
server.secret_key = 'supersecretkey'

# Initialize Dash app
# Initialize Dash app with explicit assets folder path
import os

# Get the absolute path to the assets folder
assets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

app = dash.Dash(
    __name__,
    server=server,
    suppress_callback_exceptions=True,
    assets_folder=assets_path  # Specify the absolute path to assets folder
)

# Configure MongoDB connection
# Replace with your MongoDB connection string or use environment variables
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URI)
db = client['news_app_db']
users_collection = db['users']

# News API configuration
# Get your API key from https://newsapi.org/
NEWS_API_KEY = os.environ.get('NEWS_API_KEY', '758c48dbb96c4f96b40fd091e07070ac')
NEWS_API_URL = 'https://newsapi.org/v2/top-headlines'

# For demo purposes only - in production use a proper authentication system
VALID_USERS = {"vishnu": "1234", "ayush": "5678"}


# --- Helper Functions ---

def log_login(username):
    """Log user login to MongoDB"""
    users_collection.update_one(
        {'username': username},
        {'$push': {'logins': datetime.now()},
         '$setOnInsert': {'username': username, 'created_at': datetime.now()}},
        upsert=True
    )
    print(f"User {username} login logged to MongoDB")


def get_top_news(category='general', country='us'):
    """Fetch top news from News API"""
    try:
        params = {
            'country': country,
            'category': category,
            'apiKey': NEWS_API_KEY
        }
        response = requests.get(NEWS_API_URL, params=params)
        if response.status_code == 200:
            news_data = response.json()
            return news_data.get('articles', [])
        else:
            print(f"News API error: {response.status_code}, {response.text}")
            # Return sample data if API fails
            return get_sample_news()
    except Exception as e:
        print(f"Error fetching news: {e}")
        return get_sample_news()


def get_sample_news():
    """Return sample news data when API fails"""
    return [
        {
            'title': 'Sample News Article 1',
            'description': 'This is a sample news article for testing purposes.',
            'url': 'https://example.com/news/1',
            'urlToImage': 'https://via.placeholder.com/150',
            'source': {'name': 'Sample News'}
        },
        {
            'title': 'Sample News Article 2',
            'description': 'Another sample news article for when the API is unavailable.',
            'url': 'https://example.com/news/2',
            'urlToImage': 'https://via.placeholder.com/150',
            'source': {'name': 'Sample News'}
        }
    ]


def get_news_by_source(source='bbc-news'):
    """Fetch news from a specific source"""
    try:
        params = {
            'sources': source,
            'apiKey': NEWS_API_KEY
        }
        response = requests.get('https://newsapi.org/v2/top-headlines', params=params)
        if response.status_code == 200:
            news_data = response.json()
            return news_data.get('articles', [])
        else:
            return []
    except Exception as e:
        print(f"Error fetching news by source: {e}")
        return []


def get_news_categories():
    """Return available news categories"""
    return ['business', 'entertainment', 'general', 'health', 'science', 'sports', 'technology']


# --- Layouts ---

def create_news_card(article):
    """Create a styled news card for an article"""
    # Handle missing fields gracefully
    title = article.get('title', 'No title available')
    description = article.get('description') or "No description available"
    url = article.get('url', '#')
    image_url = article.get('urlToImage', 'https://via.placeholder.com/300x200?text=No+Image')
    source = article.get('source', {}).get('name', 'Unknown Source')

    return html.Div([
        html.Div([
            html.Img(src=image_url, style={'width': '100%', 'maxHeight': '200px', 'objectFit': 'cover'})
        ]) if image_url else html.Div(),
        html.Div([
            html.H4(title, className='news-title'),
            html.P(f"Source: {source}", className='news-source'),
            html.P(description, className='news-description'),
            html.A("Read More", href=url, target='_blank', className='news-link')
        ], className='news-content')
    ], className='news-card')

def survey_layout():
    return html.Div([
        html.H2("Consent-Driven News Survey"),

        html.Label("User ID:"),
        dcc.Input(id='user-id', type='text', placeholder='Enter your user ID', style={"marginBottom": 20}),

        html.Label("What data do you consent to share?"),
        dcc.Checklist([
            "Preferred topics selected during signup",
            "Articles you read or click on",
            "Time spent reading articles",
            "Like/dislike or feedback you provide",
            "Search queries or filters used",
            "Location (to show region-specific news)",
            "Device type (for UI optimization)"
        ], id='data-consent', style={"marginBottom": 20}),

        html.Label("What topics are you interested in?"),
        dcc.Checklist([
            "Politics", "Technology", "Science", "Health", "Business", "Sports", 
            "Entertainment", "Education", "Travel", "Environment", 
            "International Affairs", "Culture / Lifestyle"
        ], id='topic-preferences', style={"marginBottom": 20}),

        html.Label("News frequency:"),
        dcc.RadioItems(["Real-time", "Few times a day", "Once a day", "Every few days"],
                       id='frequency', style={"marginBottom": 20}),

        html.Label("Preferred article length:"),
        dcc.RadioItems(["Short", "Medium", "Long"], id='length', style={"marginBottom": 20}),

        html.Label("Any content you’d like to avoid?"),
        dcc.Checklist(["Graphic", "Political", "Gossip", "Pandemic", "Crime"],
                      id='filters', style={"marginBottom": 20}),

        html.Button("Submit", id='submit-btn', n_clicks=0),
        html.Div(id='response-message', style={"marginTop": 20})
    ])


login_layout = html.Div([
    html.Div([
        html.H2("Login to News App", className='login-header'),
        html.Div([
            dcc.Input(id='username', placeholder='Username', className='login-input'),
            dcc.Input(id='password', placeholder='Password', type='password', className='login-input'),
            html.Button("Login", id='login-btn', className='login-button'),
            html.Div(id='login-output', className='login-error')
        ], className='login-form')
    ], className='login-container')
], className='login-page')

dashboard_layout = html.Div([
    html.Div([
        html.H2("📰 Personalized News Dashboard", className='dashboard-header'),
        html.Button("Logout", id='logout-btn', className='logout-btn'),
        html.Div(id='user-welcome', className='user-welcome')
    ], className='dashboard-top'),

    dcc.Tabs(id='tabs', value='top-news', children=[
        dcc.Tab(label='Top News', value='top-news'),
        dcc.Tab(label='Categories', value='categories'),
        dcc.Tab(label='Preferences', value='preferences')
    ], className='dashboard-tabs'),

    html.Div(id='tab-content', className='tab-content')
], className='dashboard-container')

# Custom CSS for better styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>News App</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }
            .login-page {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }
            .login-container {
                background: white;
                padding: 2rem;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                width: 350px;
            }
            .login-header {
                text-align: center;
                margin-bottom: 1.5rem;
                color: #333;
            }
            .login-form {
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            .login-input {
                padding: 0.75rem;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 1rem;
            }
            .login-button {
                padding: 0.75rem;
                background-color: #0066cc;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 1rem;
                cursor: pointer;
                transition: background-color 0.3s;
            }
            .login-button:hover {
                background-color: #0052a3;
            }
            .login-error {
                color: #d32f2f;
                text-align: center;
                margin-top: 0.5rem;
            }
            .dashboard-container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 1rem;
            }
            .dashboard-top {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
            }
            .dashboard-header {
                margin: 0;
                color: #333;
            }
            .logout-btn {
                padding: 0.5rem 1rem;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            .user-welcome {
                font-size: 1rem;
                color: #666;
            }
            .news-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 1.5rem;
                margin-top: 1rem;
            }
            .news-card {
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: transform 0.3s, box-shadow 0.3s;
            }
            .news-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            .news-content {
                padding: 1rem;
            }
            .news-title {
                margin-top: 0;
                font-size: 1.1rem;
                color: #333;
            }
            .news-source {
                font-size: 0.8rem;
                color: #666;
                margin-bottom: 0.5rem;
            }
            .news-description {
                color: #555;
                font-size: 0.9rem;
                line-height: 1.4;
            }
            .news-link {
                display: inline-block;
                margin-top: 0.5rem;
                color: #0066cc;
                text-decoration: none;
                font-weight: 500;
            }
            .category-selector {
                margin-bottom: 1rem;
            }
            .tab-content {
                margin-top: 1rem;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Main layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='session', storage_type='session'),
    html.Div(id='page-content')
])


# --- Callbacks ---

@callback(
    Output('page-content', 'children'),
    Input('url', 'pathname'),
    Input('session', 'data')
)
def display_page(pathname, session_data):
    if pathname == '/dashboard' and session_data and session_data.get('logged_in'):
        return dashboard_layout

    elif pathname == '/survey' and session_data and session_data.get('logged_in'):
        return survey_layout()

    return login_layout


@callback(
    Output('url', 'pathname'),
    Output('login-output', 'children'),
    Output('session', 'data'),
    Input('login-btn', 'n_clicks'),
    State('username', 'value'),
    State('password', 'value'),
    prevent_initial_call=True
)
def login_user(n_clicks, username, password):
    if username in VALID_USERS and VALID_USERS[username] == password:
        try:
            log_login(username)
        except Exception as e:
            # Continue even if MongoDB logging fails
            print(f"MongoDB logging error: {e}")

        return '/dashboard', '', {'logged_in': True, 'username': username}
    return '/', 'Invalid username or password', None


@callback(
    Output('user-welcome', 'children'),
    Input('session', 'data')
)
def update_welcome(session_data):
    if session_data and session_data.get('username'):
        return f"Welcome, {session_data['username']}!"
    return ""


@callback(
    Output('url', 'pathname', allow_duplicate=True),
    Output('session', 'data', allow_duplicate=True),
    Input('logout-btn', 'n_clicks'),
    prevent_initial_call=True
)
def logout(n_clicks):
    return '/', None


@callback(
    Output('tab-content', 'children'),
    Input('tabs', 'value'),
    Input('session', 'data')
)
def render_tab_content(tab, session_data):
    # print(session_data)
    # if not session_data or session_data.get('logged_in') == False:
    #     return html.Div("Please log in to view content")

    if tab == 'top-news':
        try:
            print("Fetching top news...")
            from news.news_fetcher import get_top_news
            news = get_top_news()
            print('news',news)
            if not news:
                print("No news articles returned")
                return html.Div([
                    html.H3("No News Available"),
                    html.P("Unable to fetch news articles. This could be due to:"),
                    html.Ul([
                        html.Li("Missing or invalid News API key"),
                        html.Li("Network connectivity issues"),
                        html.Li("News API rate limit reached")
                    ]),
                    html.P("Please check the console for more details.")
                ])

            print(f"Rendering {len(news)} news articles")
            return html.Div([
                html.H3("Today's Top Headlines"),
                html.Div([
                    create_news_card(article) for article in news
                ], className='news-grid')
            ])
        except Exception as e:
            print(f"Error in render_tab_content: {e}")
            import traceback
            traceback.print_exc()
            return html.Div([
                html.H3("Error Loading News"),
                html.P(f"An error occurred: {str(e)}"),
                html.P("Please check the console for more details.")
            ])

    elif tab == 'categories':
        try:
            from news.news_fetcher import get_news_categories
            categories = get_news_categories()
            print('categories',categories)
            return html.Div([
                html.H3("Browse News by Category"),
                html.Div([
                    dcc.Dropdown(
                        id='category-dropdown',
                        options=[{'label': cat.capitalize(), 'value': cat} for cat in categories],
                        value='general',
                        clearable=False
                    )
                ], className='category-selector'),
                html.Div(id='category-news')
            ])
        except Exception as e:
            print(f"Error loading categories: {e}")
            return html.Div([
                html.H3("Error Loading Categories"),
                html.P(f"An error occurred: {str(e)}")
            ])

    elif tab == 'preferences':
        return html.Div([
            html.H3("Personalize Your News Feed"),
            html.P("This feature is coming soon! Here you'll be able to:"),
            html.Ul([
                html.Li("Select your favorite news sources"),
                html.Li("Choose preferred categories"),
                html.Li("Set up keyword alerts"),
                html.Li("Save articles for later reading")
            ])
        ])


@callback(
    Output('category-news', 'children'),
    Input('category-dropdown', 'value'),
    prevent_initial_call=True
)
def update_category_news(category):
    news = get_top_news(category=category)
    return html.Div([
        create_news_card(article) for article in news
    ], className='news-grid')


@app.callback(
    Output("response-message", "children"),
    Input("submit-btn", "n_clicks"),
    State("user-id", "value"),
    State("data-consent", "value"),
    State("topic-preferences", "value"),
    State("frequency", "value"),
    State("length", "value"),
    State("filters", "value"),
)
def submit_survey(n_clicks, user_id, data_consent, topic_prefs, freq, length, filters):
    if n_clicks > 0:
        payload = {
            "user_id": user_id,
            "data_consent": data_consent or [],
            "topic_preferences": topic_prefs or [],
            "news_frequency": freq,
            "article_length": length,
            "content_filters": filters or []
        }
        try:
            response = requests.post("http://localhost:5000/submit-survey", json=payload)
            if response.status_code == 200:
                return "✅ Survey submitted successfully!"
            else:
                return f"❌ Error: {response.json().get('error', 'Unknown error')}"
        except Exception as e:
            return f"❌ Could not connect to backend: {str(e)}"
    return ""



# --- Main execution ---
if __name__ == '__main__':
    # Ensure the assets directory exists
    if not os.path.exists('assets'):
        os.makedirs('assets')
        print("Created assets directory")

    # Create cache directory if it doesn't exist
    if not os.path.exists(os.path.join('assets', 'cache')):
        os.makedirs(os.path.join('assets', 'cache'))
        print("Created assets/cache directory")

    print("\n=== News App ===")
    print("Starting server...")
    if NEWS_API_KEY == 'your_news_api_key':
        print("\nWARNING: You're using the default News API key placeholder.")
        print("Get your API key from https://newsapi.org/ and set it as an environment variable:")
        print("export NEWS_API_KEY=your_api_key_here")
        print("\nThe app will use sample news data for now.\n")

    try:
        # Test MongoDB connection
        client.admin.command('ping')
        print("MongoDB connection successful!")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        print("User login will still work but data won't be saved.")

    print("\nTest users available:")
    print("Username: vishnu, Password: 1234")
    print("Username: ayush, Password: 5678")

    app.run(debug=False)
