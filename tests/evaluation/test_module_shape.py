def test_semantic_scorer_importable_with_score_method():
    from evaluation.semantic_scorer import SemanticPromptScorer
    assert hasattr(SemanticPromptScorer, "score")


def test_aesthetic_scorer_importable_with_score_method():
    from evaluation.aesthetic_scorer import AestheticScorer
    assert hasattr(AestheticScorer, "score")
