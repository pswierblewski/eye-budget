import pytest

from src.bank_category_top import top_category_candidate_from_stored_json


@pytest.mark.unit
class TestTopCategoryCandidateFromStoredJson:
    def test_none(self):
        assert top_category_candidate_from_stored_json(None) is None

    def test_empty_list(self):
        assert top_category_candidate_from_stored_json([]) is None

    def test_invalid_json_string(self):
        assert top_category_candidate_from_stored_json("{") is None

    def test_picks_highest_score(self):
        raw = [
            {"category_id": 1, "category_name": "A", "category_score": 0.5},
            {"category_id": 2, "category_name": "B", "category_score": 0.9},
        ]
        assert top_category_candidate_from_stored_json(raw) == {
            "category_id": 2,
            "category_name": "B",
            "category_score": 0.9,
        }

    def test_tie_breaks_by_lower_category_id(self):
        raw = [
            {"category_id": 5, "category_name": "A", "category_score": 0.8},
            {"category_id": 3, "category_name": "B", "category_score": 0.8},
        ]
        assert top_category_candidate_from_stored_json(raw) == {
            "category_id": 3,
            "category_name": "B",
            "category_score": 0.8,
        }

    def test_json_bytes(self):
        b = b'[{"category_id":3,"category_name":"X","category_score":0.1}]'
        assert top_category_candidate_from_stored_json(b) == {
            "category_id": 3,
            "category_name": "X",
            "category_score": 0.1,
        }

    def test_skips_malformed_entries(self):
        raw = [
            {"bad": 1},
            {"category_id": 5, "category_name": "Ok", "category_score": 0.2},
        ]
        assert top_category_candidate_from_stored_json(raw) == {
            "category_id": 5,
            "category_name": "Ok",
            "category_score": 0.2,
        }
