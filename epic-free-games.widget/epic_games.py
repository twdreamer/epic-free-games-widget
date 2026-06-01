#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


EPIC_URL = (
    "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?"
    + urlencode({"locale": "zh-TW", "country": "TW", "allowCountries": "TW"})
)
STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
STEAM_REVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X) EpicFreeGamesWidget/1.0"


def fetch_json(url, params=None):
    if params:
        url += ("&" if "?" in url else "?") + urlencode(params)
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def normalize(value):
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def steam_search_url(title):
    return f"https://store.steampowered.com/search/?term={quote(title)}"


def find_steam_game(title):
    fallback = {"url": steam_search_url(title), "rating": None, "reviews": None}
    try:
        data = fetch_json(STEAM_SEARCH_URL, {"term": title, "l": "tchinese", "cc": "TW"})
        items = data.get("items") or []
        if not items:
            return fallback

        wanted = normalize(title)
        best = max(
            items[:10],
            key=lambda item: SequenceMatcher(None, wanted, normalize(item.get("name", ""))).ratio(),
        )
        ratio = SequenceMatcher(None, wanted, normalize(best.get("name", ""))).ratio()
        if ratio < 0.72:
            return fallback

        appid = best["id"]
        reviews = fetch_json(
            STEAM_REVIEWS_URL.format(appid=appid),
            {"json": 1, "language": "all", "purchase_type": "all", "filter": "summary"},
        ).get("query_summary", {})
        total = reviews.get("total_reviews", 0)
        positive = reviews.get("total_positive", 0)
        rating = round(positive * 100 / total) if total else None
        return {
            "url": f"https://store.steampowered.com/app/{appid}/",
            "rating": rating,
            "reviews": total or None,
        }
    except Exception:
        return fallback


def offer_groups(element):
    promotions = element.get("promotions") or {}
    return {
        "current": promotions.get("promotionalOffers") or [],
        "upcoming": promotions.get("upcomingPromotionalOffers") or [],
    }


def first_offer(groups):
    for group in groups:
        offers = group.get("promotionalOffers") or []
        if offers:
            return offers[0]
    return None


def epic_url(element):
    mappings = element.get("catalogNs", {}).get("mappings") or []
    slug = mappings[0].get("pageSlug") if mappings else element.get("productSlug")
    if not slug or slug == "[]":
        return "https://store.epicgames.com/zh-Hant/free-games"
    return f"https://store.epicgames.com/zh-Hant/p/{slug}"


def image_url(element):
    images = element.get("keyImages") or []
    for image_type in ("OfferImageWide", "DieselStoreFrontWide", "Thumbnail"):
        for image in images:
            if image.get("type") == image_type:
                return image.get("url")
    return None


def display_time(value):
    if not value:
        return None
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return date.astimezone().strftime("%m/%d %H:%M")


def game_data(element, offer, include_steam=False):
    result = {
        "title": element.get("title", "未知遊戲"),
        "description": element.get("description") or "",
        "epicUrl": epic_url(element),
        "image": image_url(element),
        "start": display_time(offer.get("startDate")),
        "end": display_time(offer.get("endDate")),
    }
    if include_steam:
        result["steam"] = find_steam_game(result["title"])
    return result


def main():
    payload = fetch_json(EPIC_URL)
    elements = payload["data"]["Catalog"]["searchStore"]["elements"]
    current = []
    upcoming = []

    for element in elements:
        groups = offer_groups(element)
        offer = first_offer(groups["current"])
        if offer and offer.get("discountSetting", {}).get("discountPercentage") == 0:
            current.append(game_data(element, offer, include_steam=True))

        offer = first_offer(groups["upcoming"])
        if offer and offer.get("discountSetting", {}).get("discountPercentage") == 0:
            upcoming.append(game_data(element, offer))

    print(
        json.dumps(
            {
                "updatedAt": datetime.now(timezone.utc).astimezone().strftime("%H:%M"),
                "current": current,
                "upcoming": upcoming,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        sys.exit(1)
