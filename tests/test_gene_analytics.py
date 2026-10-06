from analytics.gene_analytics import (
    GeneAnalytics,
)

class FakeHistoryRepository:
    
    def load(self):

        return [
            {
                "dna": {
                    "lighting": (
                        "golden sunlight"
                    ),
                    "camera": (
                        "wide shot"
                    ),
                },

                "combined_score": 80,
            },

            {
                "dna": {
                    "lighting": (
                        "golden sunlight"
                    ),
                    "camera": (
                        "close shot"
                    ),
                },

                "combined_score": 60,
            },
        ]
    

def test_trait_averages():
    repo = FakeHistoryRepository()

    analytics = GeneAnalytics(repo)

    result = (
        analytics.compute_trait_score()
    )

    assert (result["lighting"]["golden sunlight"] == 70.0)

    assert (result["camera"]["wide shot"] == 80.0)

    assert (result["camera"]["close shot"] == 60.0)