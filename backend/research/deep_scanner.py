"""Deep YouTube Scanner — DATA FIRST approach.

Scans hundreds of keywords across high-RPM niches to find REAL outliers:
videos with massive views from small channels. Then checks the Spanish
gap (how much competition exists in Spanish for the same topic).

Quota budget (10,000 units/day):
- search.list = 100 units each
- videos.list = 1 unit (up to 50 IDs)
- channels.list = 1 unit (up to 50 IDs)

Strategy: ~45 searches (4,500 units) + stats lookups (~500 units) = ~5,000 units
Leaves 5,000 units for deep dives on the best finds.
"""

import re
from datetime import datetime, timedelta

from backend.research.youtube_api import get_youtube_client, YOUTUBE_API_KEY


# ══════════════════════════════════════════════════════════════════════
# SEED KEYWORDS — high RPM niches to scan (in English)
# Based on strategy doc RPM tables
# ══════════════════════════════════════════════════════════════════════

SEED_KEYWORDS = {
    "finance": [
        "credit cards explained",
        "credit score tips",
        "passive income ideas",
        "index fund investing",
        "side hustle money",
        "budgeting for beginners",
        "crypto tax explained",
        "real estate investing beginner",
        "debt payoff strategy",
        "retirement planning young",
    ],
    "insurance": [
        "life insurance explained",
        "health insurance tips",
        "car insurance save money",
    ],
    "legal": [
        "tenant rights explained",
        "small claims court",
        "copyright fair use",
    ],
    "real_estate": [
        "airbnb hosting tips",
        "house flipping beginner",
        "rental property investing",
        "real estate passive income",
    ],
    "business": [
        "dropshipping tutorial",
        "amazon fba beginner",
        "online business ideas",
        "freelancing tips",
        "etsy shop tutorial",
    ],
    "marketing": [
        "email marketing tutorial",
        "seo for beginners",
        "social media marketing strategy",
        "ai marketing tools",
    ],
    "education": [
        "study techniques science",
        "learn programming free",
        "language learning tips",
    ],
    "health": [
        "intermittent fasting results",
        "home workout no equipment",
        "sleep optimization tips",
        "mental health habits",
    ],
    "tech_ai": [
        "ai tools for productivity",
        "chatgpt tutorial",
        "ai automation business",
        "best ai apps",
        "make money with ai",
    ],
    "storytelling": [
        "true crime documentary",
        "unsolved mysteries",
        "historical mysteries",
        "psychology dark facts",
        "conspiracy theories explained",
    ],
    "meditation_asmr": [
        "guided meditation sleep",
        "deep relaxation music",
        "asmr for sleep",
    ],
}


def _parse_duration_seconds(iso_duration: str) -> int:
    """Convert ISO 8601 duration (PT1H2M3S) to seconds."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration or "")
    if not match:
        return 0
    h, m, s = (int(x or 0) for x in match.groups())
    return h * 3600 + m * 60 + s


def deep_scan(
    categories: list[str] | None = None,
    max_channel_subs: int = 100_000,
    min_video_views: int = 10_000,
    min_outlier_ratio: float = 3.0,
    published_days_ago: int = 365,
    progress_callback=None,
) -> dict:
    """Massive scan across high-RPM niches to find real outliers.

    Args:
        categories: Which SEED_KEYWORDS categories to scan (None = all)
        max_channel_subs: Only flag channels smaller than this
        min_video_views: Minimum views for a video to count as outlier
        min_outlier_ratio: Minimum views/subs ratio
        published_days_ago: Only look at videos from last N days
        progress_callback: fn(message, pct) for progress updates

    Returns:
        dict with outliers, channels, stats, and scan metadata
    """
    if not YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY required for deep scan")

    yt = get_youtube_client()
    published_after = (
        datetime.utcnow() - timedelta(days=published_days_ago)
    ).strftime("%Y-%m-%dT00:00:00Z")

    # Select categories to scan
    cats = categories or list(SEED_KEYWORDS.keys())
    keywords = []
    for cat in cats:
        if cat in SEED_KEYWORDS:
            for kw in SEED_KEYWORDS[cat]:
                keywords.append((cat, kw))

    total_keywords = len(keywords)
    all_videos = []  # Raw video results
    seen_video_ids = set()

    # ── PHASE 1: Search across all keywords ──────────────────────────
    # Use "relevance" order — returns a diverse mix of channels (big + small)
    # "viewCount" skews heavily toward mega-channels which get filtered out
    for idx, (category, keyword) in enumerate(keywords):
        if progress_callback:
            pct = int((idx / total_keywords) * 50)
            progress_callback(f"Buscando: {keyword}", pct)

        try:
            search_resp = yt.search().list(
                q=keyword,
                type="video",
                part="snippet",
                maxResults=25,
                order="relevance",
                videoDuration="medium",  # 4-20 min (faceless sweet spot)
                publishedAfter=published_after,
                relevanceLanguage="en",
            ).execute()

            for item in search_resp.get("items", []):
                vid = item["id"]["videoId"]
                if vid not in seen_video_ids:
                    seen_video_ids.add(vid)
                    all_videos.append({
                        "video_id": vid,
                        "channel_id": item["snippet"]["channelId"],
                        "channel_title": item["snippet"]["channelTitle"],
                        "title": item["snippet"]["title"],
                        "search_keyword": keyword,
                        "search_category": category,
                    })
        except Exception as e:
            print(f"  [WARN] Search failed for '{keyword}': {e}")
            continue

    if progress_callback:
        progress_callback(f"Encontrados {len(all_videos)} vídeos únicos. Obteniendo estadísticas...", 50)

    # ── PHASE 2: Get video stats in batches of 50 ────────────────────
    video_stats = {}
    video_ids_list = [v["video_id"] for v in all_videos]

    for i in range(0, len(video_ids_list), 50):
        batch = video_ids_list[i:i + 50]
        try:
            resp = yt.videos().list(
                id=",".join(batch),
                part="statistics,contentDetails",
            ).execute()
            for item in resp.get("items", []):
                stats = item.get("statistics", {})
                video_stats[item["id"]] = {
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "duration_sec": _parse_duration_seconds(
                        item["contentDetails"]["duration"]
                    ),
                    "duration_raw": item["contentDetails"]["duration"],
                }
        except Exception as e:
            print(f"  [WARN] Video stats batch failed: {e}")

    # Merge stats into videos
    for v in all_videos:
        stats = video_stats.get(v["video_id"], {})
        v.update(stats)

    if progress_callback:
        progress_callback("Analizando canales...", 65)

    # ── PHASE 3: Get channel stats in batches of 50 ──────────────────
    unique_channel_ids = list({v["channel_id"] for v in all_videos})
    channel_stats = {}

    for i in range(0, len(unique_channel_ids), 50):
        batch = unique_channel_ids[i:i + 50]
        try:
            resp = yt.channels().list(
                id=",".join(batch),
                part="statistics,snippet",
            ).execute()
            for item in resp.get("items", []):
                stats = item.get("statistics", {})
                channel_stats[item["id"]] = {
                    "subscribers": int(stats.get("subscriberCount", 0)),
                    "total_views": int(stats.get("viewCount", 0)),
                    "video_count": int(stats.get("videoCount", 0)),
                    "channel_name": item["snippet"]["title"],
                    "channel_description": item["snippet"].get("description", "")[:300],
                }
        except Exception as e:
            print(f"  [WARN] Channel stats batch failed: {e}")

    # Merge channel stats and calculate outlier ratios
    for v in all_videos:
        ch = channel_stats.get(v["channel_id"], {})
        v["channel_subscribers"] = ch.get("subscribers", 0)
        v["channel_total_views"] = ch.get("total_views", 0)
        v["channel_video_count"] = ch.get("video_count", 0)
        v["channel_description"] = ch.get("channel_description", "")

        subs = v["channel_subscribers"]
        views = v.get("views", 0)

        # Key metric: how many times did this video get more views than the channel has subs
        v["views_to_subs_ratio"] = round(views / subs, 1) if subs > 0 else 0

    if progress_callback:
        progress_callback("Filtrando outliers...", 80)

    # ── PHASE 4: Find outliers ───────────────────────────────────────
    # Debug: count how many pass each filter
    has_subs = [v for v in all_videos if v["channel_subscribers"] > 0]
    small_ch = [v for v in has_subs if v["channel_subscribers"] <= max_channel_subs]
    enough_views = [v for v in small_ch if v.get("views", 0) >= min_video_views]
    good_ratio = [v for v in enough_views if v["views_to_subs_ratio"] >= min_outlier_ratio]
    long_enough = [v for v in good_ratio if v.get("duration_sec", 0) >= 240]

    print(f"  [FILTER] Total videos: {len(all_videos)}")
    print(f"  [FILTER] Has subs data: {len(has_subs)}")
    print(f"  [FILTER] Small channels (≤{max_channel_subs}): {len(small_ch)}")
    print(f"  [FILTER] Enough views (≥{min_video_views}): {len(enough_views)}")
    print(f"  [FILTER] Good ratio (≥{min_outlier_ratio}): {len(good_ratio)}")
    print(f"  [FILTER] Long enough (≥240s): {len(long_enough)}")

    outliers = long_enough
    outliers.sort(key=lambda x: x["views_to_subs_ratio"], reverse=True)

    # Also find "rising channels" — small but growing fast
    rising_channels = {}
    for v in all_videos:
        cid = v["channel_id"]
        subs = v["channel_subscribers"]
        if 1000 <= subs <= max_channel_subs and v.get("views", 0) >= 10000:
            if cid not in rising_channels:
                rising_channels[cid] = {
                    "channel_id": cid,
                    "channel_name": v["channel_title"],
                    "subscribers": subs,
                    "best_videos": [],
                    "categories": set(),
                }
            rising_channels[cid]["best_videos"].append({
                "title": v["title"],
                "views": v.get("views", 0),
                "ratio": v["views_to_subs_ratio"],
                "keyword": v["search_keyword"],
            })
            rising_channels[cid]["categories"].add(v["search_category"])

    # Sort rising channels by their best video ratio
    for ch in rising_channels.values():
        ch["best_videos"].sort(key=lambda x: x["ratio"], reverse=True)
        ch["top_ratio"] = ch["best_videos"][0]["ratio"] if ch["best_videos"] else 0
        ch["categories"] = list(ch["categories"])

    rising_list = sorted(rising_channels.values(), key=lambda x: x["top_ratio"], reverse=True)

    # ── PHASE 5: Group outliers by category ──────────────────────────
    category_summary = {}
    for v in outliers:
        cat = v["search_category"]
        if cat not in category_summary:
            category_summary[cat] = {
                "category": cat,
                "outlier_count": 0,
                "avg_ratio": 0,
                "best_ratio": 0,
                "total_views": 0,
                "examples": [],
            }
        category_summary[cat]["outlier_count"] += 1
        category_summary[cat]["total_views"] += v.get("views", 0)
        if v["views_to_subs_ratio"] > category_summary[cat]["best_ratio"]:
            category_summary[cat]["best_ratio"] = v["views_to_subs_ratio"]
        if len(category_summary[cat]["examples"]) < 5:
            category_summary[cat]["examples"].append({
                "title": v["title"],
                "channel": v["channel_title"],
                "views": v.get("views", 0),
                "subs": v["channel_subscribers"],
                "ratio": v["views_to_subs_ratio"],
                "keyword": v["search_keyword"],
            })

    for cat in category_summary.values():
        if cat["outlier_count"] > 0:
            cat["avg_ratio"] = round(
                sum(e["ratio"] for e in cat["examples"]) / len(cat["examples"]), 1
            )

    categories_ranked = sorted(
        category_summary.values(),
        key=lambda x: (x["outlier_count"], x["best_ratio"]),
        reverse=True,
    )

    if progress_callback:
        progress_callback("Scan completo.", 100)

    return {
        "scan_metadata": {
            "keywords_searched": total_keywords,
            "total_videos_found": len(all_videos),
            "unique_channels_analyzed": len(unique_channel_ids),
            "outliers_found": len(outliers),
            "filters": {
                "max_channel_subs": max_channel_subs,
                "min_video_views": min_video_views,
                "min_outlier_ratio": min_outlier_ratio,
                "published_days_ago": published_days_ago,
            },
            "timestamp": datetime.utcnow().isoformat(),
        },
        "outliers": outliers[:50],  # Top 50 outliers
        "categories_ranked": categories_ranked,
        "rising_channels": rising_list[:20],
        "scan_stats": {
            "by_category": {
                cat: len([v for v in all_videos if v["search_category"] == cat])
                for cat in set(v["search_category"] for v in all_videos)
            },
        },
    }


def check_spanish_gap(outliers: list[dict], top_n: int = 10) -> list[dict]:
    """For the top outlier topics, check how much competition exists in Spanish.

    This implements Rule 6 (EN→ES strategy): find what works in English,
    check if there's a gap in Spanish.
    """
    if not YOUTUBE_API_KEY:
        return []

    yt = get_youtube_client()
    results = []

    # Extract unique keywords from top outliers
    seen_keywords = set()
    keywords_to_check = []
    for v in outliers[:top_n * 3]:  # Check more to get enough unique keywords
        kw = v.get("search_keyword", "")
        if kw and kw not in seen_keywords:
            seen_keywords.add(kw)
            keywords_to_check.append({
                "en_keyword": kw,
                "category": v.get("search_category", ""),
                "en_views": v.get("views", 0),
                "en_channel_subs": v.get("channel_subscribers", 0),
                "en_ratio": v.get("views_to_subs_ratio", 0),
            })
        if len(keywords_to_check) >= top_n:
            break

    # Rough translations for common keywords (AI could do this better)
    # For now, search with the same keyword — YouTube handles multilingual
    for kw_data in keywords_to_check:
        try:
            # Search in Spanish
            search_resp = yt.search().list(
                q=kw_data["en_keyword"],
                type="video",
                part="snippet",
                maxResults=10,
                order="viewCount",
                videoDuration="medium",
                relevanceLanguage="es",
            ).execute()

            es_videos = search_resp.get("items", [])

            # Get stats for Spanish results
            es_video_ids = [item["id"]["videoId"] for item in es_videos]
            es_stats = {}
            if es_video_ids:
                resp = yt.videos().list(
                    id=",".join(es_video_ids),
                    part="statistics",
                ).execute()
                for item in resp.get("items", []):
                    es_stats[item["id"]] = int(
                        item.get("statistics", {}).get("viewCount", 0)
                    )

            es_total_views = sum(es_stats.values())
            es_max_views = max(es_stats.values()) if es_stats else 0

            kw_data["es_results_count"] = len(es_videos)
            kw_data["es_total_views"] = es_total_views
            kw_data["es_max_views"] = es_max_views
            kw_data["gap_score"] = round(
                kw_data["en_views"] / max(es_max_views, 1), 1
            )
            results.append(kw_data)

        except Exception as e:
            print(f"  [WARN] Spanish gap check failed for '{kw_data['en_keyword']}': {e}")

    # Sort by gap score (higher = bigger opportunity in Spanish)
    results.sort(key=lambda x: x.get("gap_score", 0), reverse=True)
    return results
