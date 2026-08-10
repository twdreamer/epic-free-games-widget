#!/usr/bin/env python3
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen


EPIC_URL = (
    "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?"
    + urlencode({"locale": "zh-TW", "country": "TW", "allowCountries": "TW"})
)
STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
STEAM_REVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X) EpicFreeGamesWidget/1.0"
CACHE_PATH = Path(__file__).with_name("epic_games_cache.json")
IMAGE_CACHE_DIR = Path(__file__).with_name("image_cache")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
IMAGE_CACHE_WIDTH = 160
IMAGE_CACHE_QUALITY = 82
CACHE_RECIPE = f"v2-{IMAGE_CACHE_WIDTH}-jpeg{IMAGE_CACHE_QUALITY}"
SIPS_PATH = "/usr/bin/sips"
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


def fetch_bytes(url):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/*,*/*;q=0.8"})
    with urlopen(request, timeout=20) as response:
        return response.read()


def load_cache():
    if not CACHE_PATH.exists():
        return None
    with CACHE_PATH.open(encoding="utf-8") as cache_file:
        payload = json.load(cache_file)
    payload = active_cached_payload(payload)
    if not payload:
        delete_cache()
        return None
    normalize_cached_images(payload)
    prune_image_cache(payload)
    save_cache(payload)
    return payload


def save_cache(payload):
    temp_path = CACHE_PATH.with_suffix(".json.tmp")
    with temp_path.open("w", encoding="utf-8") as cache_file:
        json.dump(payload, cache_file, ensure_ascii=False, indent=2)
        cache_file.write("\n")
    temp_path.replace(CACHE_PATH)


def delete_cache():
    for path in (CACHE_PATH, CACHE_PATH.with_suffix(".json.tmp")):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    shutil.rmtree(IMAGE_CACHE_DIR, ignore_errors=True)


def all_games(payload):
    return (payload.get("current") or []) + (payload.get("upcoming") or [])


def parse_iso(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def active_cached_payload(payload):
    now = datetime.now(timezone.utc)
    current = []
    upcoming = []

    def collect(game, original_section):
        start = parse_iso(game.get("startIso"))
        end = parse_iso(game.get("endIso"))
        if end and end <= now:
            return
        if start and start <= now:
            current.append(game)
            return
        if start:
            upcoming.append(game)
            return
        if original_section == "current":
            current.append(game)
        else:
            upcoming.append(game)

    for game in payload.get("current") or []:
        collect(game, "current")
    for game in payload.get("upcoming") or []:
        collect(game, "upcoming")

    if not current and not upcoming:
        return None

    return {**payload, "current": current, "upcoming": upcoming}


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


def legacy_image_cache_path(url):
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        suffix = ".jpg"
    digest = sha256(url.encode("utf-8")).hexdigest()[:20]
    return IMAGE_CACHE_DIR / f"{digest}{suffix}"


def image_cache_path(url):
    cache_key = f"{CACHE_RECIPE}:{url}"
    digest = sha256(cache_key.encode("utf-8")).hexdigest()[:20]
    return IMAGE_CACHE_DIR / f"{digest}.jpg"


def source_image_suffix(url):
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in IMAGE_EXTENSIONS else ".jpg"


def render_thumbnail(source_path, destination_path):
    result = subprocess.run(
        [
            SIPS_PATH,
            "--setProperty",
            "format",
            "jpeg",
            "--setProperty",
            "formatOptions",
            str(IMAGE_CACHE_QUALITY),
            "--resampleHeightWidthMax",
            str(IMAGE_CACHE_WIDTH),
            str(source_path),
            "--out",
            str(destination_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
    )
    if result.returncode != 0 or not destination_path.exists():
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(message or "無法建立遊戲縮圖")


def cache_thumbnail(source_path, destination_path):
    IMAGE_CACHE_DIR.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".thumbnail-", dir=IMAGE_CACHE_DIR) as temp_dir:
        temp_path = Path(temp_dir) / "thumbnail.jpg"
        render_thumbnail(source_path, temp_path)
        if temp_path.stat().st_size == 0:
            raise RuntimeError("遊戲縮圖是空檔案")
        temp_path.replace(destination_path)


def download_thumbnail(url, destination_path):
    IMAGE_CACHE_DIR.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".download-", dir=IMAGE_CACHE_DIR) as temp_dir:
        source_path = Path(temp_dir) / f"source{source_image_suffix(url)}"
        source_path.write_bytes(fetch_bytes(url))
        cache_thumbnail(source_path, destination_path)


def local_image_src(path):
    widget_dir = Path(__file__).parent.name
    return f"{widget_dir}/{IMAGE_CACHE_DIR.name}/{path.name}"


def normalize_cached_images(payload):
    for game in all_games(payload):
        cached_path_value = game.get("imageCachePath")
        if not cached_path_value:
            continue
        existing_path = Path(cached_path_value)
        remote_image = game.get("remoteImage")
        optimized_path = image_cache_path(remote_image) if remote_image else None

        if (
            optimized_path
            and not optimized_path.exists()
            and existing_path.exists()
            and existing_path.stat().st_size > 0
        ):
            try:
                cache_thumbnail(existing_path, optimized_path)
            except Exception:
                pass

        path = optimized_path if optimized_path and optimized_path.exists() else existing_path
        if path.exists() and path.stat().st_size > 0:
            game["image"] = local_image_src(path)
            game["imageCachePath"] = str(path)


def cache_game_image(game):
    image = game.get("image")
    if not image or image.startswith("file://"):
        return

    path = image_cache_path(image)
    legacy_path = legacy_image_cache_path(image)
    try:
        if not path.exists() or path.stat().st_size == 0:
            if legacy_path.exists() and legacy_path.stat().st_size > 0:
                cache_thumbnail(legacy_path, path)
            else:
                download_thumbnail(image, path)

        game["remoteImage"] = image
        game["image"] = local_image_src(path)
        game["imageCachePath"] = str(path)
    except Exception:
        fallback_path = path if path.exists() and path.stat().st_size > 0 else legacy_path
        if fallback_path.exists() and fallback_path.stat().st_size > 0:
            game["remoteImage"] = image
            game["image"] = local_image_src(fallback_path)
            game["imageCachePath"] = str(fallback_path)


def cache_images(payload):
    for game in all_games(payload):
        cache_game_image(game)

    prune_image_cache(payload)


def prune_image_cache(payload):
    referenced_paths = {
        Path(game["imageCachePath"]).resolve()
        for game in all_games(payload)
        if game.get("imageCachePath")
    }
    if IMAGE_CACHE_DIR.exists():
        for path in IMAGE_CACHE_DIR.iterdir():
            if path.is_file() and path.resolve() not in referenced_paths:
                path.unlink()


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
        "startIso": offer.get("startDate"),
        "endIso": offer.get("endDate"),
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
    cache_images(payload)
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
