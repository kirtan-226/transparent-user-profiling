from typing import List, Dict


def analyze_activity(saved_articles: List[Dict], preferences: Dict) -> List[str]:
    """Return a list of recommended categories based on saved articles and user preferences."""
    category_counts = {}
    for article in saved_articles:
        category = article.get("category")
        if not category:
            continue
        category_counts[category] = category_counts.get(category, 0) + 1

    # Sort categories by frequency
    sorted_categories = [cat for cat, _ in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)]

    # Start with most frequent categories
    recommended = []
    for cat in sorted_categories:
        if cat not in recommended:
            recommended.append(cat)

    # Append user preferred categories
    for cat in preferences.get("categories", []):
        if cat not in recommended:
            recommended.append(cat)

    # Limit to top 5 categories
    return recommended[:5]