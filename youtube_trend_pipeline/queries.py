"""Balanced discovery queries for the ten requested subject areas."""

QUERY_MATRIX: dict[str, tuple[str, ...]] = {
    "AI and technology": (
        "artificial intelligence documentary",
        "AI agents future of work",
        "semiconductor industry analysis",
        "NVIDIA AI chips explained",
        "future technology documentary",
        "cybersecurity technology analysis",
    ),
    "Business and billionaires": (
        "business empire documentary",
        "billionaire company analysis",
        "hidden monopoly documentary",
        "startup rise and fall",
        "corporate strategy explained",
        "global supply chain business",
    ),
    "Engineering and manufacturing": (
        "engineering megaproject documentary",
        "inside factory manufacturing",
        "how it is made engineering",
        "semiconductor manufacturing",
        "industrial engineering explained",
        "abandoned megaproject",
    ),
    "History and mysteries": (
        "history mystery documentary",
        "archaeological discovery documentary",
        "lost civilization explained",
        "unsolved historical mystery",
        "ancient engineering documentary",
        "forgotten history documentary",
    ),
    "Energy and infrastructure": (
        "energy infrastructure documentary",
        "nuclear energy future",
        "power grid engineering",
        "renewable energy analysis",
        "oil gas industry documentary",
        "infrastructure megaproject",
    ),
    "Space and science": (
        "space exploration documentary",
        "SpaceX Starship engineering",
        "astronomy discovery explained",
        "physics documentary",
        "NASA mission analysis",
        "science breakthrough documentary",
    ),
    "Military technology": (
        "military technology documentary",
        "fighter jet engineering",
        "naval technology explained",
        "drone warfare analysis",
        "defense industry documentary",
        "military engineering history",
    ),
    "Economics and geopolitics": (
        "global economics documentary",
        "geopolitics analysis",
        "China economy explained",
        "trade war analysis",
        "economic crisis documentary",
        "globalization supply chains",
    ),
    "Consumer technology": (
        "consumer technology analysis",
        "smartphone industry documentary",
        "electric vehicle market analysis",
        "future gadgets explained",
        "technology product failure",
        "big tech ecosystem analysis",
    ),
    "Robotics and automation": (
        "humanoid robots documentary",
        "factory automation",
        "robotics engineering explained",
        "autonomous vehicles technology",
        "industrial robots future",
        "robotics startup analysis",
    ),
}


def iter_queries() -> list[tuple[str, str]]:
    """Interleave categories so a low request budget remains balanced."""
    return [
        (category, queries[index])
        for index in range(max(map(len, QUERY_MATRIX.values())))
        for category, queries in QUERY_MATRIX.items()
        if index < len(queries)
    ]
