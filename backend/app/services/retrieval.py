"""BM25 passage ranking, shared by the chat endpoint and the compliance check."""

import math
import re
from collections import Counter

_WORD_RE = re.compile(r"[a-z0-9]+")

_K1 = 1.5
_B = 0.75

STOPWORDS = frozenset(
    "a an and any are as at be been by can do does for from has have how in is it its "
    "me my of on or our shall should so that the their them there these this those to "
    "under up was were what when where which who whom why will with within would you "
    "your".split()
)


def terms(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(text.lower()) if w not in STOPWORDS and len(w) > 1]


def rank(query: str, passages: list[str]) -> list[int]:
    """Passage indices, best match first, scored with BM25.

    Ranking used to be a fuzzy string-similarity score, which measures how alike two
    strings look rather than whether one answers the other. Similarity peaks when
    the two strings are the same length, so a 40-character heading beat the
    3000-character provision holding the answer: "What deadlines are mentioned?"
    against a 1300-section Act retrieved three headings totalling 293 characters,
    and the model — correctly — answered that it did not know.

    BM25 scores what retrieval actually depends on: how rare a shared term is across
    this document (a match on "deadline" means far more than a match on "care"), how
    often it occurs in the passage, and the passage's length, discounted rather than
    rewarded.
    """
    docs = [Counter(terms(text)) for text in passages]
    if not docs:
        return []
    lengths = [sum(d.values()) or 1 for d in docs]
    avg_len = sum(lengths) / len(lengths)
    n = len(docs)

    query_terms = set(terms(query))
    document_freq = Counter(term for d in docs for term in query_terms if term in d)
    idf = {
        term: math.log(1 + (n - df + 0.5) / (df + 0.5))
        for term, df in document_freq.items()
    }

    def score(i: int) -> float:
        doc, length = docs[i], lengths[i]
        total = 0.0
        for term, weight in idf.items():
            tf = doc.get(term, 0)
            if tf:
                total += weight * (tf * (_K1 + 1)) / (tf + _K1 * (1 - _B + _B * length / avg_len))
        return total

    # A query sharing no term with any passage scores every passage zero; falling
    # back to the longest ones at least hands the model substantive text to read.
    return sorted(range(n), key=lambda i: (score(i), lengths[i]), reverse=True)
