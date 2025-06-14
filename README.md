News App - Project Structure
The project is structured as follows:
news-app/
│
├── app.py                   # Main application file 
├── database/
│   └── mongo_handler.py     # MongoDB connection and functions
├── news/
│   └── news_fetcher.py      # News API handler
├── assets/
│   ├── custom.css           # Custom CSS styles
│   ├── favicon.ico          # Favicon for the app
│   └── cache/               # Cache directory for news data
└── requirements.txt         # Project dependencies
Getting Started

Install the required dependencies:
pip install -r requirements.txt

Set up environment variables (optional):
export NEWS_API_KEY=your_api_key_here
export MONGO_URI=your_mongodb_connection_string

Run the application:
python app.py

Open your browser and navigate to:
http://127.0.0.1:8050/

Features

User authentication with MongoDB
News feed from News API
Category-based news browsing
Responsive design with custom CSS

Selecting the "general" category in the preferences will display news from all
available categories. The "General News" section in the app shows a mix of
articles spanning each category when this option is chosen.

Additional Information

The app uses the News API (https://newsapi.org/) to fetch news data. You'll need to register for a free API key.
MongoDB is used for user management and storing preferences. Make sure MongoDB is installed and running.
The assets folder contains CSS and other static files that Dash automatically serves.
