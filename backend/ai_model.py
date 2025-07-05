from typing import Dict, List, Set, Union
from collections import Counter
import re
import nltk
from nltk import pos_tag
from nltk.corpus import wordnet
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

def _ensure_nltk_data() -> None:
    """Download required NLTK data if not already present."""
    packages = {
        "punkt": "tokenizers/punkt",
        "averaged_perceptron_tagger": "taggers/averaged_perceptron_tagger",
        "wordnet": "corpora/wordnet",
    }
    for pkg, res in packages.items():
        try:
            nltk.data.find(res)
        except LookupError:
            nltk.download(pkg)


_ensure_nltk_data()

WORD_RE = re.compile(r"[a-z0-9_-]+")
STEMMER = PorterStemmer()
def _normalize(word: str) -> str:
    """Return a lowercased stem for consistent keyword matching."""
    return STEMMER.stem(word.lower())

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
            stem = _normalize(word)
            if stem not in seen:
                keywords.append(stem)
                seen.add(stem)
            try:
                synsets = wordnet.synsets(word)
            except LookupError:
                synsets = []
            for syn in synsets[:2]:
                for lemma in syn.lemmas()[:2]:
                    syn_word = _normalize(lemma.name().replace("_", "-"))
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
    category_counts: Counter = Counter()
    location_counts: Counter = Counter()
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
        location_counts.update(user_profile.get("locations", {}))
        
    sorted_categories = [cat for cat, _ in category_counts.most_common()]
    rec_categories: List[str] = sorted_categories.copy()

    for cat in preferences.get("categories", []):
        if cat not in rec_categories:
            rec_categories.append(cat)

    sorted_keywords = [w for w, _ in keyword_counts.most_common()]
    rec_keywords: List[str] = sorted_keywords.copy()
    pref_kw_string = preferences.get("keywords", "")
    if pref_kw_string:
        for kw in extract_keywords(pref_kw_string):
            if kw not in rec_keywords:
                rec_keywords.append(kw)

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
        "keywords": rec_keywords[:5],
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
            score += kw_scores.get(word, 0) * 1.5
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


def rank_categories_by_liking(user_keywords: List[str], category_docs: Dict[str, str]) -> List[str]:
    """Rank categories using a TF‑IDF similarity between user keywords and
    category documents."""
    if not category_docs:
        return []

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(category_docs.values())
    if user_keywords:
        user_vec = vectorizer.transform([" ".join(user_keywords)])
    else:
        user_vec = vectorizer.transform([" "])

    scores = linear_kernel(user_vec, tfidf_matrix).flatten()
    ranked = sorted(zip(category_docs.keys(), scores), key=lambda x: x[1], reverse=True)
    return [cat for cat, _ in ranked]