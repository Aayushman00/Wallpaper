

from __future__ import annotations

class GeneAnalytics:

    def __init__(
            self,
            history_repo,
        ) -> None:

        self.history_repo = (
            history_repo
        )
    
    def compute_trait_score(
            self,
    ) -> dict[str, dict[str, float]]:
        
        history = self.history_repo.load()

        trait_totals = {}
        trait_counts = {}

        for record in history:
            dna = record.get("dna", {})
            score = record.get("combined_score", 0)

            for trait, value in dna.items():
                if not isinstance(value, str):
                    continue

                if trait not in trait_totals:
                    trait_totals[trait] = {}

                if trait not in trait_counts:
                    trait_counts[trait] = {}

                
                if value not in trait_totals[trait]:
                    trait_totals[trait][value] = 0
                
                if value not in trait_counts[trait]:
                    trait_counts[trait][value] = 0

                
                trait_totals[trait][value] += score
                trait_counts[trait][value] += 1
        
        trait_averages = {}
        for trait, values in trait_totals.items():
            trait_averages[trait] = {}

            for value, total in values.items():
                count = trait_counts[trait][value]

                average = total / count

                trait_averages[trait][value] = round(
                    average,
                    2,
                )

        

        return trait_averages