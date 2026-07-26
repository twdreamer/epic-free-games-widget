#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


EPIC_URL = (
    "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?"
    + urlencode({"locale": "zh-TW", "country": "TW", "allowCountries": "TW"})
)
STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
STEAM_REVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X) EpicFreeGamesWidget/1.0"
CACHE_PATH = Path(__file__).with_name("epic_games_cache.json")
STEAM_EXTRA_PATTERN = re.compile(
    r"\b(demo|soundtrack|ost|artbook|playtest|beta|dlc)\b|試玩|原聲|美術|設定集",
    re.IGNORECASE,
)


def fetch_json(url, params=None):
    if params:
        url += ("&" if "?" in url else "?") + urlencode(params)
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def load_cache():
    if not CACHE_PATH.exists():
        return None
    with CACHE_PATH.open(encoding="utf-8") as cache_file:
        return json.load(cache_file)


def save_cache(payload):
    temp_path = CACHE_PATH.with_suffix(".json.tmp")
    with temp_path.open("w", encoding="utf-8") as cache_file:
        json.dump(payload, cache_file, ensure_ascii=False, indent=2)
        cache_file.write("\n")
    temp_path.replace(CACHE_PATH)


def normalize(value):
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def search_title(value):
    title = value.strip()
    quoted = re.fullmatch(r"[《「『](.+)[》」』]", title)
    if quoted:
        title = quoted.group(1)
    return title.strip()


def steam_search_url(title):
    return f"https://store.steampowered.com/search/?term={quote(search_title(title))}"


def is_steam_extra(item):
    name = item.get("name") or ""
    return item.get("type") != "app" or bool(STEAM_EXTRA_PATTERN.search(name))


def find_steam_game(title):
    fallback = {"url": steam_search_url(title), "rating": None, "reviews": None}
    try:
        term = search_title(title)
        data = fetch_json(STEAM_SEARCH_URL, {"term": term, "l": "tchinese", "cc": "TW"})
        items = data.get("items") or []
        if not items:
            return fallback

        viable_items = [item for item in items[:10] if not is_steam_extra(item)]
        if not viable_items:
            return fallback

        wanted = normalize(term)
        best = max(
            viable_items,
            key=lambda item: SequenceMatcher(None, wanted, normalize(item.get("name", ""))).ratio(),
        )
        ratio = SequenceMatcher(None, wanted, normalize(best.get("name", ""))).ratio()
        if ratio < 0.72:
            top = viable_items[0]
            if top != items[0] or not top.get("price"):
                return fallback
            best = top

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


def free_offers(groups):
    offers = []
    for group in groups:
        for offer in group.get("promotionalOffers") or []:
            if offer.get("discountSetting", {}).get("discountPercentage") == 0:
                offers.append(offer)
    return offers


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


def fetch_games():
    payload = fetch_json(EPIC_URL)
    elements = payload["data"]["Catalog"]["searchStore"]["elements"]
    current = []
    upcoming = []

    for element in elements:
        groups = offer_groups(element)
        offers = free_offers(groups["current"])
        if offers:
            offer = offers[0]
            current.append(game_data(element, offer, include_steam=True))

        offers = free_offers(groups["upcoming"])
        if offers:
            offer = offers[0]
            upcoming.append(game_data(element, offer))

    now = datetime.now(timezone.utc).astimezone()
    return {
        "updatedAt": now.strftime("%H:%M"),
        "updatedDate": now.strftime("%Y-%m-%d"),
        "cached": False,
        "current": current,
        "upcoming": upcoming,
    }


def main():
    payload = fetch_games()
    save_cache(payload)
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        cache = load_cache()
        if cache:
            cache["cached"] = True
            cache["cacheReason"] = str(error)
            print(json.dumps(cache, ensure_ascii=False))
            sys.exit(0)

        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        sys.exit(1)
