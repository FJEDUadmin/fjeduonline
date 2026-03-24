from __future__ import annotations

import math
from collections import Counter, defaultdict

from adductomics_api.schemas import CandidateAdduct, PathwayScore


def _comb(n: int, r: int) -> int:
    if r < 0 or r > n:
        return 0
    return math.comb(n, r)


def _hypergeom_p_value(k: int, n: int, k_population: int, population_size: int) -> float:
    """
    Right-tail hypergeometric p-value:
      P(X >= k), X ~ Hypergeom(N=population_size, K=k_population, n=n)
    """
    denominator = _comb(population_size, n)
    if denominator == 0:
        return 1.0

    p = 0.0
    upper = min(n, k_population)
    for i in range(k, upper + 1):
        p += (_comb(k_population, i) * _comb(population_size - k_population, n - i)) / denominator
    return min(max(p, 0.0), 1.0)


def score_pathways(
    candidates: list[CandidateAdduct], pathway_population: dict[str, int], total_population: int
) -> list[PathwayScore]:
    pathway_hits = Counter([c.pathway for c in candidates if c.pathway])
    if not pathway_hits:
        return []

    conf_by_pathway: dict[str, list[float]] = defaultdict(list)
    for candidate in candidates:
        if candidate.pathway:
            conf_by_pathway[candidate.pathway].append(candidate.confidence_score)

    n = len([c for c in candidates if c.pathway])
    scores: list[PathwayScore] = []
    for pathway, hits in pathway_hits.items():
        k_population = pathway_population.get(pathway, 0)
        p_value = _hypergeom_p_value(
            k=hits, n=n, k_population=k_population, population_size=total_population
        )
        mean_conf = sum(conf_by_pathway[pathway]) / len(conf_by_pathway[pathway])
        enrichment_score = -math.log10(max(p_value, 1e-300)) * mean_conf
        scores.append(
            PathwayScore(
                pathway=pathway,
                hits=hits,
                population_size=k_population,
                enrichment_score=round(enrichment_score, 6),
                p_value=round(p_value, 8),
            )
        )

    scores.sort(key=lambda s: s.enrichment_score, reverse=True)
    return scores
