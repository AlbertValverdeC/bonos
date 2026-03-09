"""Google Trends integration — real demand data.

Uses pytrends to check actual search demand on YouTube.
"""

from pytrends.request import TrendReq


def check_trend(keyword: str, timeframe: str = "today 12-m") -> dict:
    """Check Google Trends data for a keyword filtered to YouTube Search.

    timeframe: 'today 12-m' (last year), 'today 5-y' (5 years), etc.
    Returns trend direction and interest score.
    """
    try:
        pytrends = TrendReq(hl="es")
        pytrends.build_payload(
            [keyword],
            cat=0,
            timeframe=timeframe,
            gprop="youtube",  # Filter to YouTube Search
        )

        interest = pytrends.interest_over_time()
        if interest.empty:
            return {
                "keyword": keyword,
                "status": "no_data",
                "trend": "unknown",
                "avg_interest": 0,
            }

        values = interest[keyword].tolist()
        avg = sum(values) / len(values)

        # Compare last quarter vs first quarter to determine trend
        quarter_len = max(len(values) // 4, 1)
        first_quarter_avg = sum(values[:quarter_len]) / quarter_len
        last_quarter_avg = sum(values[-quarter_len:]) / quarter_len

        if first_quarter_avg == 0:
            change_pct = 100 if last_quarter_avg > 0 else 0
        else:
            change_pct = round(((last_quarter_avg - first_quarter_avg) / first_quarter_avg) * 100, 1)

        if change_pct > 20:
            trend = "rising"
        elif change_pct < -20:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "keyword": keyword,
            "status": "ok",
            "trend": trend,
            "change_pct": change_pct,
            "avg_interest": round(avg, 1),
            "current_interest": values[-1] if values else 0,
            "peak_interest": max(values) if values else 0,
            "data_points": len(values),
        }

    except Exception as e:
        return {
            "keyword": keyword,
            "status": "error",
            "trend": "unknown",
            "error": str(e),
        }


def compare_topics(keywords: list[str], timeframe: str = "today 12-m") -> dict:
    """Compare multiple topics on Google Trends (YouTube filter).

    Returns relative interest for each keyword.
    """
    if len(keywords) > 5:
        keywords = keywords[:5]  # Google Trends limit

    try:
        pytrends = TrendReq(hl="es")
        pytrends.build_payload(
            keywords,
            cat=0,
            timeframe=timeframe,
            gprop="youtube",
        )

        interest = pytrends.interest_over_time()
        if interest.empty:
            return {"keywords": keywords, "status": "no_data", "results": []}

        results = []
        for kw in keywords:
            if kw not in interest.columns:
                continue
            values = interest[kw].tolist()
            results.append({
                "keyword": kw,
                "avg_interest": round(sum(values) / len(values), 1),
                "current": values[-1] if values else 0,
                "peak": max(values) if values else 0,
            })

        results.sort(key=lambda x: x["avg_interest"], reverse=True)
        return {"keywords": keywords, "status": "ok", "results": results}

    except Exception as e:
        return {"keywords": keywords, "status": "error", "error": str(e)}


def get_related_queries(keyword: str) -> dict:
    """Get related/rising queries for a keyword on YouTube.

    These are real search suggestions — gold for video ideas.
    """
    try:
        pytrends = TrendReq(hl="es")
        pytrends.build_payload(
            [keyword],
            cat=0,
            timeframe="today 12-m",
            gprop="youtube",
        )

        related = pytrends.related_queries()
        kw_data = related.get(keyword, {})

        top_queries = []
        if kw_data.get("top") is not None:
            top_queries = kw_data["top"].to_dict("records")

        rising_queries = []
        if kw_data.get("rising") is not None:
            rising_queries = kw_data["rising"].to_dict("records")

        return {
            "keyword": keyword,
            "status": "ok",
            "top_queries": top_queries[:15],
            "rising_queries": rising_queries[:15],
        }

    except Exception as e:
        return {"keyword": keyword, "status": "error", "error": str(e)}
