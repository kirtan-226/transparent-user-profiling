from typing import Dict, List, Union, Set
from collections import Counter
import re
import nltk
from nltk import pos_tag
from nltk.corpus import wordnet
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

nltk.download("punkt")
nltk.download("averaged_perceptron_tagger")
nltk.download("wordnet")

WORD_RE = re.compile(r"[a-z0-9_-]+")
STEMMER = PorterStemmer()
STOP_WORDS = set(nltk.corpus.stopwords.words("english"))
AVAILABLE_LOCATIONS = ["USA", "China", "India", "Russia", "UK", "Germany"]

def _normalize(word: str) -> str:
    return STEMMER.stem(word.lower())

def extract_keywords(text: str) -> List[str]:
    tokens = [t for t in WORD_RE.findall(text.lower()) if t not in STOP_WORDS]
    keywords = []
    seen: Set[str] = set()
    try:
        tagged = pos_tag(tokens)
    except Exception:
        tagged = [(t, "") for t in tokens]

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


def build_user_profile(articles: List[Dict]) -> Dict[str, Counter]:
    keyword_counter = Counter()
    source_counter = Counter()
    category_counter = Counter()
    location_counter = Counter()

    for article in articles:
        weight = article.get("interaction", 1)
        text = f"{article.get('title', '')} {article.get('description', '')}"
        for word in extract_keywords(text):
            keyword_counter[word] += weight
        source = article.get("source")
        category = article.get("category")
        if source:
            source_counter[source] += weight
        if category:
            category_counter[category] += weight
        for word in extract_keywords(text):
            for loc in AVAILABLE_LOCATIONS:
                if word.lower() == loc.lower():
                    location_counter[loc] += weight

    return {
        "keywords": keyword_counter,
        "sources": source_counter,
        "categories": category_counter,
        "locations": location_counter,
    }


def recommend_articles(user_profile: Dict[str, Counter], articles: List[Dict]) -> List[Dict]:
    recs = []
    for article in articles:
        score = 0
        explanation = []
        text = f"{article.get('title', '')} {article.get('description', '')}"
        keywords = extract_keywords(text)

        for kw in keywords:
            score += 1.5 * user_profile["keywords"].get(kw, 0)
            if user_profile["keywords"].get(kw):
                explanation.append(f"Keyword match: {kw}")

        if article.get("source") in user_profile["sources"]:
            score += user_profile["sources"][article["source"]]
            explanation.append(f"Source match: {article['source']}")

        if article.get("category") in user_profile["categories"]:
            score += user_profile["categories"][article["category"]]
            explanation.append(f"Category match: {article['category']}")

        article["score"] = score
        article["explanation"] = explanation
        recs.append(article)

    return sorted(recs, key=lambda x: x["score"], reverse=True)


def rank_categories_by_tfidf(user_keywords: List[str], category_docs: Dict[str, str]) -> List[str]:
    if not category_docs:
        return []
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(category_docs.values())
    user_vec = vectorizer.transform([" ".join(user_keywords)])
    scores = cosine_similarity(user_vec, tfidf_matrix).flatten()
    ranked = sorted(zip(category_docs.keys(), scores), key=lambda x: x[1], reverse=True)
    return [cat for cat, _ in ranked]


def apply_time_decay(profile: Counter, decay_factor: float = 0.95) -> Counter:
    return Counter({k: v * decay_factor for k, v in profile.items()})


def normalize_counter(counter: Counter) -> Dict[str, float]:
    total = sum(counter.values())
    return {k: v / total for k, v in counter.items()} if total else {}

def merge_preferences(profile1: Dict[str, Counter], profile2: Dict[str, Counter]) -> Dict[str, Counter]:
    merged = {}
    for key in profile1.keys():
        merged[key] = profile1[key] + profile2.get(key, Counter())
    return merged
