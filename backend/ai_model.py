from typing import List, Dict
from collections import Counter
import re

WORD_RE = re.compile(r"[a-z0-9_-]+")

AVAILABLE_LOCATIONS = ["USA", "China", "India", "Russia", "UK", "Germany"]

def extract_keywords(text: str) -> List[str]:
    """Return sanitized keywords from a block of text."""
    return WORD_RE.findall(text.lower())

def analyze_activity(saved_articles: List[Dict], preferences: Dict) -> Dict[str, List[str]]:
    """Return recommended categories and locations based on liked articles and user preferences."""
    category_counts: Counter = Counter()
    location_counts: Counter = Counter()

    for article in saved_articles:
        category = article.get("category")
        if category:
            category_counts[category] += 1

        text = f"{article.get('title', '')} {article.get('description', '')}"
        for loc in AVAILABLE_LOCATIONS:
            if loc.lower() in text:
                location_counts[loc] += 1

    sorted_categories = [cat for cat, _ in category_counts.most_common()]
    sorted_locations = [loc for loc, _ in location_counts.most_common()]

    rec_categories: List[str] = sorted_categories.copy()
    for cat in preferences.get("categories", []):
        if cat not in rec_categories:
            rec_categories.append(cat)

    rec_locations: List[str] = sorted_locations.copy()

    for loc in preferences.get("locations", []):
        if loc not in rec_locations:
            rec_locations.append(loc)

    return {
        "categories": rec_categories[:5],
        "locations": rec_locations[:5],
    }


def rank_articles(articles: List[Dict], user_profile: Dict, rec_locations: List[str]) -> List[Dict]:
    """Score and rank articles based on a user's interest profile."""
    cat_scores = user_profile.get("categories", {})
    src_scores = user_profile.get("sources", {})
    kw_scores = user_profile.get("keywords", {})

    for article in articles:
        article.setdefault("explanation", "")
        article["explanation"] += " | Recommended based on your activity"
        if rec_locations:
            article["explanation"] += f" | Locations: {', '.join(rec_locations)}"

        score = 0
        cat = article.get("category")
        src = article.get("source")
        text = f"{article.get('title', '')} {article.get('description', '')}".lower()
        if cat:
            score += cat_scores.get(cat, 0)
        if src:
            score += src_scores.get(src, 0)
        for word in extract_keywords(text):
            score += kw_scores.get(word, 0)
        article["_score"] = score

    articles.sort(key=lambda a: a.get("_score", 0), reverse=True)

    for article in articles:
        article.pop("_score", None)
        explanations = []
        cat = article.get("category")
        src = article.get("source")
        if cat and cat in cat_scores:
            explanations.append(f"Category match ({cat_scores[cat]})")
        if src and src in src_scores:
            explanations.append(f"Source match ({src_scores[src]})")
        text = f"{article.get('title', '')} {article.get('description', '')}"
        for word in extract_keywords(text):
            if word in kw_scores:
                explanations.append(f"Keyword match ({word})")
                break
        if explanations:
            article["explanation"] += " | " + ", ".join(explanations)

    return articles