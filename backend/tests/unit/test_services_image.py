import os
import pytest
from concurrent.futures.process import BrokenProcessPool
from unittest.mock import MagicMock, patch

from PIL import Image

from src.services.preprocessing import PreprocessingService
from src.services.text_localization import TextLocalizationService


def _create_jpeg(tmp_path, width: int = 100, height: int = 200, name: str = "input.jpg") -> str:
    """Create a synthetic JPEG at tmp_path/<name> and return its absolute path."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    path = str(tmp_path / name)
    img.save(path, format="JPEG")
    return path


# Canned PaddleOCR legacy-format result: one page, one line
_CANNED_PADDLE_RESULT = [
    [
        [[[10, 10], [200, 10], [200, 30], [10, 30]], ["Mleko 2%", 0.99]],
    ]
]


@pytest.mark.unit
class TestPreprocessingService:
    def test_preprocess_returns_new_path(self, tmp_path):
        # Arrange — absolute input_path bypasses input_dir (os.path.join semantics)
        input_path = _create_jpeg(tmp_path)
        svc = PreprocessingService()
        svc.input_dir = ""
        svc.output_dir = str(tmp_path / "out")

        # Act
        os.makedirs(svc.output_dir, exist_ok=True)
        output_path = svc.preprocess_image(input_path)

        # Assert
        assert os.path.exists(output_path)
        assert output_path != input_path

    def test_preprocess_output_is_half_size(self, tmp_path):
        # Arrange — 100×200 image should become 50×100
        input_path = _create_jpeg(tmp_path, width=100, height=200)
        svc = PreprocessingService()
        svc.input_dir = ""
        svc.output_dir = str(tmp_path)

        # Act
        output_path = svc.preprocess_image(input_path)

        # Assert
        with Image.open(output_path) as out_img:
            assert out_img.width == 50
            assert out_img.height == 100


@pytest.mark.unit
class TestTextLocalizationService:
    def test_detect_returns_parsed_lines(self):
        # Arrange — mock the process pool so no subprocess is spawned
        mock_future = MagicMock()
        mock_future.result.return_value = _CANNED_PADDLE_RESULT
        mock_executor = MagicMock()
        mock_executor.submit.return_value = mock_future

        with patch("src.services.text_localization._get_executor", return_value=mock_executor):
            svc = TextLocalizationService()

            # Act
            result = svc.detect("fake/path.jpg")

        # Assert
        assert len(result) == 1
        polygon, text, score = result[0]
        assert text == "Mleko 2%"
        assert score == pytest.approx(0.99)

    def test_detect_broken_pool_retries_once(self):
        # Arrange — first call raises BrokenProcessPool, second succeeds
        mock_good_future = MagicMock()
        mock_good_future.result.return_value = _CANNED_PADDLE_RESULT

        mock_broken_future = MagicMock()
        mock_broken_future.result.side_effect = BrokenProcessPool("broken")

        call_count = [0]
        mock_executor = MagicMock()

        def submit_side_effect(*args):
            call_count[0] += 1
            return mock_broken_future if call_count[0] == 1 else mock_good_future

        mock_executor.submit.side_effect = submit_side_effect

        with (
            patch("src.services.text_localization._get_executor", return_value=mock_executor),
            patch("src.services.text_localization._reset_executor"),
        ):
            svc = TextLocalizationService()

            # Act — should not raise despite broken pool on first attempt
            result = svc.detect("fake/path.jpg")

        # Assert — retried and succeeded
        assert len(result) == 1

    async def test_detect_async_delegates_to_detect(self):
        # Arrange
        canned_line = ([[0, 0], [100, 0], [100, 20], [0, 20]], "Test text", 0.95)
        svc = TextLocalizationService()
        svc.detect = MagicMock(return_value=[canned_line])

        # Act
        result = await svc.detect_async("fake/path.jpg")

        # Assert
        svc.detect.assert_called_once_with("fake/path.jpg")
        assert result == [canned_line]

    def test_parse_result_empty_returns_empty(self):
        # Arrange
        svc = TextLocalizationService()

        # Act / Assert
        assert svc._parse_result(None) == []
        assert svc._parse_result([]) == []

    def test_parse_result_skips_falsy_page(self):
        # Arrange — result has one None page
        svc = TextLocalizationService()

        # Act
        result = svc._parse_result([None])

        # Assert
        assert result == []

    def test_parse_result_new_format_dict(self):
        # Arrange — PaddleOCR 2.10+ dict format
        svc = TextLocalizationService()
        page = {
            "rec_texts": ["Mleko"],
            "rec_scores": [0.99],
            "rec_polys": [[[10, 10], [200, 10], [200, 30], [10, 30]]],
        }

        # Act
        result = svc._parse_result([page])

        # Assert
        assert len(result) == 1
        _, text, score = result[0]
        assert text == "Mleko"
        assert score == pytest.approx(0.99)

    def test_parse_result_legacy_format(self):
        # Arrange — legacy list-of-lists format
        svc = TextLocalizationService()
        result = svc._parse_result(_CANNED_PADDLE_RESULT)

        # Assert
        assert len(result) == 1
        _, text, score = result[0]
        assert text == "Mleko 2%"

    def test_parse_result_legacy_text_info_as_string(self):
        # Arrange — text_info is a plain string (not list/tuple)
        svc = TextLocalizationService()
        page = [[
            [[10, 10], [200, 10], [200, 30], [10, 30]],
            "PlainText",
        ]]

        # Act
        result = svc._parse_result([page])

        # Assert
        assert len(result) == 1
        _, text, score = result[0]
        assert text == "PlainText"
        assert score == 1.0

    def test_parse_result_bad_item_skipped(self):
        # Arrange — item with unparseable polygon
        svc = TextLocalizationService()
        bad_page = [[
            "not-a-polygon",
            ["text", 0.9],
        ]]

        # Act — should not raise
        result = svc._parse_result([bad_page])

        # Assert — bad item silently skipped
        assert result == []


@pytest.mark.unit
class TestToSerializable:
    """Tests for _to_serializable() — must convert PaddleOCR result objects to
    plain Python structures before they cross the ProcessPoolExecutor boundary."""

    def test_none_result_returns_empty(self):
        # Arrange / Act / Assert
        from src.services.text_localization import _to_serializable
        assert _to_serializable(None) == []

    def test_empty_result_returns_empty(self):
        # Arrange / Act / Assert
        from src.services.text_localization import _to_serializable
        assert _to_serializable([]) == []

    def test_new_dict_format(self):
        # Arrange — PaddleOCR 2.10+ dict-based page
        from src.services.text_localization import _to_serializable
        page = {
            "rec_texts": ["Mleko 2%"],
            "rec_scores": [0.99],
            "rec_polys": [[[10, 10], [200, 10], [200, 30], [10, 30]]],
        }

        # Act
        result = _to_serializable([page])

        # Assert — normalised to legacy shape: [[polygon, [text, score]]]
        assert len(result) == 1
        page_out = result[0]
        assert len(page_out) == 1
        polygon, text_score = page_out[0]
        assert polygon == [[10, 10], [200, 10], [200, 30], [10, 30]]
        assert text_score == ["Mleko 2%", pytest.approx(0.99)]

    def test_legacy_list_format(self):
        # Arrange — legacy [polygon, [text, score]] page
        from src.services.text_localization import _to_serializable
        page = [
            [[[10, 10], [200, 10], [200, 30], [10, 30]], ["Chleb", 0.95]],
        ]

        # Act
        result = _to_serializable([page])

        # Assert — legacy format preserved correctly
        assert len(result) == 1
        page_out = result[0]
        assert len(page_out) == 1
        polygon, text_score = page_out[0]
        assert polygon == [[10, 10], [200, 10], [200, 30], [10, 30]]
        assert text_score[0] == "Chleb"
        assert text_score[1] == pytest.approx(0.95)

    def test_falsy_page_skipped(self):
        # Arrange — result with a None page followed by a valid page
        from src.services.text_localization import _to_serializable
        valid_page = [
            [[[0, 0], [100, 0], [100, 20], [0, 20]], ["OK", 0.9]],
        ]

        # Act
        result = _to_serializable([None, valid_page])

        # Assert — None page skipped; valid page present as empty list + items
        # first entry is [] (falsy page → empty list), second has one item
        assert result[0] == []
        assert len(result[1]) == 1
