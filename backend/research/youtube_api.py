"""YouTube Data API v3 — real data for research.

Uses the free YouTube Data API to:
- Search for channels in a niche
- Get video statistics (views, likes, comments)
- Find outlier videos (views >> channel average)
- Analyze competition level
"""

from googleapiclient.discovery import build

from backend.config.settings import OPENAI_API_KEY


# YouTube Data API uses a simple API key (no OAuth needed for read-only)
# We'll reuse the same env var pattern
import os
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")


def get_youtube_client():
    if not YOUTUBE_API_KEY:
        raise ValueError(
            "YOUTUBE_API_KEY not set. Get one free at: "
            "https://console.cloud.google.com/apis/credentials "
            "(enable 'YouTube Data API v3')"
        )
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def search_channels(query: str, max_results: int = 15) -> list[dict]:
    """Search for YouTube channels in a niche."""
    yt = get_youtube_client()

    # Search for channels
    search_resp = yt.search().list(
        q=query,
        type="channel",
        part="snippet",
        maxResults=max_results,
        order="relevance",
    ).execute()

    channel_ids = [item["snippet"]["channelId"] for item in search_resp.get("items", [])]
    if not channel_ids:
        return []

    # Get channel statistics
    channels_resp = yt.channels().list(
        id=",".join(channel_ids),
        part="snippet,statistics,contentDetails",
    ).execute()

    results = []
    for ch in channels_resp.get("items", []):
        stats = ch.get("statistics", {})
        results.append({
            "channel_id": ch["id"],
            "title": ch["snippet"]["title"],
            "description": ch["snippet"].get("description", "")[:200],
            "subscribers": int(stats.get("subscriberCount", 0)),
            "total_views": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "thumbnail": ch["snippet"]["thumbnails"].get("default", {}).get("url", ""),
        })

    return sorted(results, key=lambda x: x["subscribers"], reverse=True)


def get_channel_videos(channel_id: str, max_results: int = 30) -> list[dict]:
    """Get recent videos from a channel with their stats."""
    yt = get_youtube_client()

    # Get uploads playlist
    channel_resp = yt.channels().list(
        id=channel_id,
        part="contentDetails",
    ).execute()

    items = channel_resp.get("items", [])
    if not items:
        return []

    uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Get video IDs from uploads playlist
    playlist_resp = yt.playlistItems().list(
        playlistId=uploads_id,
        part="contentDetails",
        maxResults=max_results,
    ).execute()

    video_ids = [item["contentDetails"]["videoId"] for item in playlist_resp.get("items", [])]
    if not video_ids:
        return []

    # Get video statistics
    videos_resp = yt.videos().list(
        id=",".join(video_ids),
        part="snippet,statistics,contentDetails",
    ).execute()

    videos = []
    for v in videos_resp.get("items", []):
        stats = v.get("statistics", {})
        videos.append({
            "video_id": v["id"],
            "title": v["snippet"]["title"],
            "published_at": v["snippet"]["publishedAt"],
            "duration": v["contentDetails"]["duration"],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "thumbnail": v["snippet"]["thumbnails"].get("high", {}).get("url", ""),
        })

    return videos


def find_outliers(channel_id: str, threshold: float = 3.0) -> dict:
    """Find outlier videos that perform well above channel average.

    Returns channel info + videos sorted by outlier score.
    threshold: minimum multiplier over average (3.0 = 3x average views)
    """
    videos = get_channel_videos(channel_id, max_results=30)
    if not videos:
        return {"channel_id": channel_id, "videos": [], "avg_views": 0}

    avg_views = sum(v["views"] for v in videos) / len(videos)
    if avg_views == 0:
        avg_views = 1

    for v in videos:
        v["outlier_score"] = round(v["views"] / avg_views, 1)

    # Filter and sort by outlier score
    outliers = [v for v in videos if v["outlier_score"] >= threshold]
    outliers.sort(key=lambda x: x["outlier_score"], reverse=True)

    return {
        "channel_id": channel_id,
        "avg_views": int(avg_views),
        "total_videos": len(videos),
        "outliers": outliers,
        "all_videos": sorted(videos, key=lambda x: x["views"], reverse=True),
    }


def search_niche_videos(query: str, max_results: int = 30,
                         published_after: str = "", min_duration: str = "medium") -> list[dict]:
    """Search for videos in a niche with filters.

    min_duration: 'short' (<4min), 'medium' (4-20min), 'long' (>20min)
    published_after: ISO date string (e.g. '2025-01-01T00:00:00Z')
    """
    yt = get_youtube_client()

    params = {
        "q": query,
        "type": "video",
        "part": "snippet",
        "maxResults": max_results,
        "order": "viewCount",
        "videoDuration": min_duration,
        "relevanceLanguage": "en",  # Search in English to find what works
    }
    if published_after:
        params["publishedAfter"] = published_after

    search_resp = yt.search().list(**params).execute()

    video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]
    if not video_ids:
        return []

    # Get full video stats
    videos_resp = yt.videos().list(
        id=",".join(video_ids),
        part="snippet,statistics,contentDetails",
    ).execute()

    results = []
    for v in videos_resp.get("items", []):
        stats = v.get("statistics", {})
        results.append({
            "video_id": v["id"],
            "title": v["snippet"]["title"],
            "channel_title": v["snippet"]["channelTitle"],
            "channel_id": v["snippet"]["channelId"],
            "published_at": v["snippet"]["publishedAt"],
            "duration": v["contentDetails"]["duration"],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "thumbnail": v["snippet"]["thumbnails"].get("high", {}).get("url", ""),
        })

    return sorted(results, key=lambda x: x["views"], reverse=True)


def analyze_niche_competition(query: str) -> dict:
    """Analyze competition level for a niche.

    Searches for channels and videos, then calculates:
    - Number of active channels
    - Average subscriber count
    - Views-to-subscribers ratio (virality indicator)
    - Top performing videos
    """
    channels = search_channels(query, max_results=15)
    videos = search_niche_videos(query, max_results=20, min_duration="long")

    if not channels:
        return {"error": "No channels found", "query": query}

    total_subs = sum(c["subscribers"] for c in channels)
    avg_subs = total_subs // len(channels) if channels else 0

    # Find channels with high view-to-sub ratio (good for faceless)
    for ch in channels:
        if ch["subscribers"] > 0 and ch["video_count"] > 0:
            avg_views_per_video = ch["total_views"] / ch["video_count"]
            ch["views_per_sub"] = round(avg_views_per_video / ch["subscribers"], 2)
        else:
            ch["views_per_sub"] = 0

    # Competition score (lower = better opportunity)
    big_channels = len([c for c in channels if c["subscribers"] > 100000])
    medium_channels = len([c for c in channels if 10000 <= c["subscribers"] <= 100000])

    if big_channels >= 10:
        competition_level = "alta"
        competition_score = 8
    elif big_channels >= 5:
        competition_level = "media-alta"
        competition_score = 6
    elif medium_channels >= 5:
        competition_level = "media"
        competition_score = 4
    else:
        competition_level = "baja"
        competition_score = 2

    return {
        "query": query,
        "channels_found": len(channels),
        "avg_subscribers": avg_subs,
        "competition_level": competition_level,
        "competition_score": competition_score,
        "top_channels": channels[:10],
        "top_videos": videos[:10],
        "opportunity_indicators": {
            "small_channels_with_big_views": len([
                c for c in channels
                if c["subscribers"] < 50000 and c["views_per_sub"] > 5
            ]),
            "avg_views_per_sub": round(
                sum(c.get("views_per_sub", 0) for c in channels) / len(channels), 2
            ) if channels else 0,
        },
    }
