from typing import List, Dict

AVAILABLE_LOCATIONS = ["USA", "China", "India", "Russia", "UK", "Germany"]


def analyze_activity(saved_articles: List[Dict], preferences: Dict) -> Dict[str, List[str]]:
    """Return recommended categories and locations based on liked articles and preferences."""
    category_counts: Dict[str, int] = {}
    location_counts: Dict[str, int] = {}

def analyze_activity(saved_articles: List[Dict], preferences: Dict) -> List[str]:
    for article in saved_articles:
        category = article.get("category")
        if category:
            category_counts[category] = category_counts.get(category, 0) + 1

        text = f"{article.get('title', '')} {article.get('description', '')}".lower()
        for loc in AVAILABLE_LOCATIONS:
            if loc.lower() in text:
                location_counts[loc] = location_counts.get(loc, 0) + 1

    sorted_categories = [cat for cat, _ in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)]
    sorted_locations = [loc for loc, _ in sorted(location_counts.items(), key=lambda x: x[1], reverse=True)]

    rec_categories: List[str] = []
    for cat in sorted_categories:
        if cat not in rec_categories:
            rec_categories.append(cat)

    # Append user preferred categories
    for cat in preferences.get("categories", []):
         if cat not in rec_categories:
            rec_categories.append(cat)

    rec_locations: List[str] = []
    for loc in sorted_locations:
        if loc not in rec_locations:
            rec_locations.append(loc)

    for loc in preferences.get("locations", []):
        if loc not in rec_locations:
            rec_locations.append(loc)

    # Limit to top 5 categories
    return {
        "categories": rec_categories[:5],
        "locations": rec_locations[:5],
    }