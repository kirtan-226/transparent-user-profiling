# frontend/app.py
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    __package__ = "frontend"
from .api_client import APIClient
from .components import (
    create_login_layout,
    create_register_layout,
    create_news_feed_layout,
)
from .callbacks import register_callbacks

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

def create_app():
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True
    )

    api_client = APIClient(API_BASE_URL)

    app.layout = html.Div([
        dcc.Location(id='url', refresh=False),
        dcc.Store(id='auth-store', storage_type='session'),
        html.Div(id='page-content')
    ])

    register_callbacks(app, api_client)

    return app

app = create_app()
server = app.server

if __name__ == '__main__':
    app.run(debug=True, port=8050)