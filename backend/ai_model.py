from typing import List, Dict
from collections import Counter

AVAILABLE_LOCATIONS = ["USA", "China", "India", "Russia", "UK", "Germany"]


def analyze_activity(saved_articles: List[Dict], preferences: Dict) -> Dict[str, List[str]]:
    """Return recommended categories and locations based on liked articles and user preferences."""
    category_counts: Counter = Counter()
    location_counts: Counter = Counter()

    for article in saved_articles:
        category = article.get("category")
        if category:
            category_counts[category] += 1

        text = f"{article.get('title', '')} {article.get('description', '')}".lower()
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

    # Limit to top 5 categories
    return {
        "categories": rec_categories[:5],
        "locations": rec_locations[:5],
    }