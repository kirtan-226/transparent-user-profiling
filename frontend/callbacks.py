from dash import html, Input, Output, State, callback_context
import dash
import dash_bootstrap_components as dbc
import json
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    __package__ = "frontend"

from .components import (
    create_login_layout,
    create_register_layout,
    create_news_feed_layout,
    create_news_card,
)
from .api_client import format_error_detail

ALL_NEWS_CATEGORIES = ["business", "entertainment", "general", "health", "science", "sports", "technology"]


def register_callbacks(app, api_client):

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
                detail = format_error_detail(error_data, "Registration failed")
                return detail, "", dash.no_update
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
                detail = format_error_detail(error_data, "Login failed")
                return detail, dash.no_update, dash.no_update
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

    @app.callback(
        Output('suggested-news-container', 'children'),
        Output('general-news-container', 'children'),
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
            return [], []

        try:
            api_client.set_token(auth_data['token'])
            categories = categories or ALL_NEWS_CATEGORIES
            keywords = keywords or ""
            pers_resp = api_client.get_personalized_news()
            pers_articles = []
            if pers_resp.status_code == 200:
                pers_data = pers_resp.json()
                pers_articles = pers_data.get('articles', [])

            gen_categories = categories
            if not gen_categories or (len(gen_categories) == 1 and gen_categories[0] == "general"):
                gen_categories = ALL_NEWS_CATEGORIES
            gen_resp = api_client.fetch_news(gen_categories, keywords, locations or [])
            gen_articles = []
            if gen_resp.status_code == 200:
                gen_data = gen_resp.json()
                gen_articles = gen_data.get('articles', [])

            pers_ids = {a.get('article_id') for a in pers_articles}
            gen_articles = [a for a in gen_articles if a.get('article_id') not in pers_ids]

            liked_ids = []
            liked_resp = api_client.get_liked_articles()
            if liked_resp.status_code == 200:
                liked_data = liked_resp.json()
                liked_ids = [a['article_id'] for a in liked_data.get('liked_articles', [])]

            def _cards(articles):
                if not articles:
                    return [html.Div("No articles found.", className="text-center text-muted")]
                return [create_news_card(a, liked=a['article_id'] in liked_ids) for a in articles]

            return _cards(pers_articles), _cards(gen_articles)
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
                    data = response.json()
                    articles = data.get('saved_articles', [])
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

    @app.callback(
        Output({'type': 'read-article-btn', 'index': dash.dependencies.MATCH}, 'children'),
        [Input({'type': 'read-article-btn', 'index': dash.dependencies.MATCH}, 'n_clicks')],
        [State('auth-store', 'data')],
        prevent_initial_call=True
    )
    def record_read(n_clicks, auth_data):
        if n_clicks and auth_data and auth_data.get('token'):
            try:
                ctx = callback_context
                if ctx.triggered:
                    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
                    article_id = json.loads(button_id)['index']
                    api_client.set_token(auth_data['token'])
                    api_client.read_article(article_id)
            except Exception:
                pass
        return "Read More"