from pipeline.web_search import rank_results

def test_social_bonus_resorts_without_discarding_non_social_result():
    ranked = rank_results([
        {"link": "https://example.org/article", "title": "Article", "relevance": 0.70},
        {"link": "https://instagram.com/p/a", "title": "Post", "relevance": 0.65},
    ])
    assert [item["source_domain"] for item in ranked] == ["instagram.com", "example.org"]
    assert ranked[0]["social_bonus"] == 0.10
    assert len(ranked) == 2

def test_high_relevance_non_social_is_still_kept_and_can_win():
    ranked = rank_results([{"link": "https://news.example/a", "relevance": .99}, {"link": "https://reddit.com/r/x", "relevance": .01}])
    assert ranked[0]["source_domain"] == "news.example"
