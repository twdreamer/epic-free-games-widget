import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "epic_games.py"
SPEC = importlib.util.spec_from_file_location("epic_games", MODULE_PATH)
epic_games = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(epic_games)


class SteamRatingTests(unittest.TestCase):
    def test_uses_new_reviews_service_and_calculates_rating(self):
        search_response = {
            "items": [
                {
                    "id": 821250,
                    "type": "app",
                    "name": "Flotsam",
                    "price": {"currency": "TWD", "final": 37800},
                }
            ]
        }
        reviews_response = {
            "response": {
                "query_summary": {
                    "total_positive": 3845,
                    "total_negative": 882,
                    "total_reviews": 4727,
                }
            }
        }

        with patch.object(
            epic_games,
            "fetch_json",
            side_effect=[search_response, reviews_response],
        ) as fetch_json:
            result = epic_games.find_steam_game("Flotsam")

        self.assertEqual(result["url"], "https://store.steampowered.com/app/821250/")
        self.assertEqual(result["rating"], 81)
        self.assertEqual(result["reviews"], 4727)

        reviews_url, reviews_params = fetch_json.call_args_list[1].args
        self.assertEqual(reviews_url, epic_games.STEAM_REVIEWS_URL)
        request_data = json.loads(reviews_params["input_json"])
        self.assertEqual(request_data["appid"], 821250)
        self.assertEqual(request_data["languages"], ["all"])
        self.assertEqual(request_data["purchase_type"], 1)

    def test_preserves_search_fallback_and_records_api_error(self):
        search_response = {
            "items": [{"id": 627690, "type": "app", "name": "Idle Champions"}]
        }

        with patch.object(
            epic_games,
            "fetch_json",
            side_effect=[search_response, ValueError("invalid review response")],
        ):
            result = epic_games.find_steam_game("Idle Champions")

        self.assertIsNone(result["rating"])
        self.assertIn("search/?term=Idle%20Champions", result["url"])
        self.assertEqual(result["error"], "ValueError: invalid review response")


if __name__ == "__main__":
    unittest.main()
