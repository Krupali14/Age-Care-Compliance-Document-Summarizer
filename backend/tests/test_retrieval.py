from app.services.retrieval import rank, terms


def test_terms_drops_stopwords_and_single_characters():
    assert terms("What are the deadlines in this section?") == ["deadlines", "section"]


def test_rank_prefers_the_passage_sharing_rare_terms():
    passages = [
        "General information about care and services provided to residents.",
        "The provider must notify the Commission of a reportable incident within 24 hours.",
        "Care plans are reviewed annually.",
    ]
    assert rank("reportable incident notification", passages)[0] == 1


def test_rank_returns_every_index_even_when_nothing_matches():
    passages = ["alpha beta", "gamma delta"]
    assert sorted(rank("zzzz", passages)) == [0, 1]
