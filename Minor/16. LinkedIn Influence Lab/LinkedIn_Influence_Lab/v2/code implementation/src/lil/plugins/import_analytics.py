PLUGIN = {
    "id": "import_analytics", "name": "Analytics CSV importer (Taplio / LinkedIn)", "category": "import",
    "icon": "📥", "default_enabled": True,
    "description": "Maps columns from Taplio or LinkedIn analytics exports (Impressions, Reactions, Comments, "
                   "Reposts, Profile views...) onto the tracking sheet. Free tiers expose fewer metrics, so "
                   "manual entry is always available.",
    "fields": [],
}

ALIASES = {
    "post_id": ["post_id", "post id", "draft id", "id"],
    "published_date": ["published_date", "date", "published", "post date", "publish date", "created at"],
    "impressions": ["impressions", "views", "post impressions"],
    "likes": ["likes", "reactions", "like count"],
    "comments": ["comments", "comment count"],
    "shares": ["shares", "reposts", "repost count"],
    "profile_visits": ["profile_visits", "profile views", "profile visits", "profile viewers"],
}


def map_columns(df):
    """Return a copy of df with canonical column names; unknown columns are dropped."""
    lower = {c.lower().strip(): c for c in df.columns}
    out = {}
    for canon, names in ALIASES.items():
        for n in names:
            if n in lower:
                out[canon] = df[lower[n]]
                break
    import pandas as pd
    return pd.DataFrame(out)
