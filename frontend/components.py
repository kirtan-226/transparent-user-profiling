from dash import dcc, html
import dash_bootstrap_components as dbc


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
                            value=[],
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

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    html.Div("News Preferences", className="card-header"),
                    dbc.CardBody([
                        html.H6("Categories"),
                        dbc.Checklist(
                            id="category-filter",
                            options=[
                                {"label": "Business", "value": "business"},
                                {"label": "Entertainment", "value": "entertainment"},
                                {"label": "General", "value": "general"},
                                {"label": "Health", "value": "health"},
                                {"label": "Science", "value": "science"},
                                {"label": "Sports", "value": "sports"},
                                {"label": "Technology", "value": "technology"},
                            ],
                            value=[],
                            inline=True,
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

            dbc.Col([
                html.H4("Suggested News", className="mb-4"),
                html.Div(id="suggested-news-container", children=[
                    dbc.Spinner(color="primary", type="grow", fullscreen=False)
                ]),
                html.Hr(),
                html.H4("General News", className="mb-4"),
                html.Div(id="general-news-container", children=[
                    dbc.Spinner(color="primary", type="grow", fullscreen=False)
                ]),
            ], width=9)
        ])
    ], fluid=True)


def create_news_card(article, liked=False):
    like_label = "Liked!" if liked else "Like"
    info_id = {"type": "info-btn", "index": article["article_id"]}
    explanation = article.get("explanation", "") or "No explanation available"
    return dbc.Card([
        dbc.CardImg(
            src=article.get("urlToImage") if article.get("urlToImage") else "https://via.placeholder.com/300x200?text=No+Image",
            top=True
        ),
        dbc.CardBody([
            html.H5(article["title"], className="card-title"),
            html.P(article["description"], className="card-text"),
            html.P([
                html.Small(
                    f"Source: {article['source']} | Category: {article['category'].capitalize()}",
                    className="text-muted"
                )
            ]),
            dbc.Button(
                "i",
                id=info_id,
                color="secondary",
                outline=True,
                size="sm",
                className="me-2",
                style={"padding": "0.25rem 0.5rem"},
            ),
            dbc.Tooltip(explanation, target=info_id, placement="top"),
            dbc.Button(
                "Read More",
                id={"type": "read-article-btn", "index": article["article_id"]},
                href=article["url"],
                target="_blank",
                color="primary",
                className="me-2",
            ),
            dbc.Button(
                "Save Article",
                id={"type": "save-article-btn", "index": article["article_id"]},
                color="success",
                className="me-2",
            ),
            dbc.Button(
                like_label,
                id={"type": "like-article-btn", "index": article["article_id"]},
                color="danger",
            ),
        ])
    ], className="mb-4 shadow-sm")