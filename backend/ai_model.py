from typing import Dict, List, Set, Union
from collections import Counter
import re
import nltk
from nltk import pos_tag
from nltk.corpus import wordnet

WORD_RE = re.compile(r"[a-z0-9_-]+")

STOP_WORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "to",
    "of",
    "for",
    "and",
    "or",
    "in",
    "on",
    "at",
    "with",
    "without",
    "by",
}


AVAILABLE_LOCATIONS = ["USA", "China", "India", "Russia", "UK", "Germany"]

def extract_keywords(text: str) -> List[str]:
    """Return sanitized keywords from a block of text.

    Only nouns and verbs are kept, and common stop words are removed. Synonyms
    for each keyword are also included using WordNet.
    """
    tokens = [t for t in WORD_RE.findall(text.lower()) if t not in STOP_WORDS]

    keywords: List[str] = []
    try:
        tagged = pos_tag(tokens)
    except Exception:
        tagged = [(t, "") for t in tokens]

    seen: Set[str] = set()
    for word, tag in tagged:
        if tag.startswith("NN") or tag.startswith("VB"):
            if word not in seen:
                keywords.append(word)
                seen.add(word)
            try:
                synsets = wordnet.synsets(word)
            except LookupError:
                synsets = []
            for syn in synsets:
                for lemma in syn.lemmas():
                    syn_word = lemma.name().replace("_", "-").lower()
                    if syn_word not in STOP_WORDS and syn_word not in seen:
                        keywords.append(syn_word)
                        seen.add(syn_word)
    return keywords


def analyze_activity(
    activity_data: Union[Dict, List[Dict]], preferences: Dict
) -> Dict[str, List[str]]:
    """Return recommended categories and locations using a user's interest profile.

    The first argument may be either a saved user profile dictionary or a list of
    previously interacted articles for backward compatibility.
    """
    keyword_counts: Counter = Counter()
    if isinstance(activity_data, list):
        for article in activity_data:
            if not isinstance(article, dict):
                continue
            category = article.get("category")
            if category:
                category_counts[category] += 1
            text = f"{article.get('title', '')} {article.get('description', '')}"
            for word in extract_keywords(text):
                keyword_counts[word] += 1
    else:
        user_profile = activity_data or {}
        category_counts.update(user_profile.get("categories", {}))
        keyword_counts.update(user_profile.get("keywords", {}))

    sorted_locations = [loc for loc, _ in location_counts.most_common()]
    location_counts: Counter = Counter()
    for word, cnt in keyword_counts.items():
        for loc in AVAILABLE_LOCATIONS:
            if word.lower() == loc.lower():
                location_counts[loc] += cnt

    sorted_locations = [loc for loc, _ in location_counts.most_common()]
    rec_locations: List[str] = sorted_locations.copy()

    for loc in preferences.get("locations", []):
        if loc not in rec_locations:
            rec_locations.append(loc)

    return {
        "categories": rec_categories[:5],
        "locations": rec_locations[:5],
    }


def rank_articles(
    articles: List[Dict], user_profile: Dict, rec_locations: List[str]
) -> List[Dict]:
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