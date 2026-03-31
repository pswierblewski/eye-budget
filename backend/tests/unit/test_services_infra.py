import os
import pytest
from unittest.mock import MagicMock, patch

from minio.error import S3Error

from src.services.minio_storage import MinioStorageService
from src.services.pusher_service import PusherService


def _make_minio_service() -> tuple[MinioStorageService, MagicMock]:
    """Build a MinioStorageService with a mocked Minio client."""
    with patch("src.services.minio_storage.Minio") as MockMinio:
        mock_client = MagicMock()
        MockMinio.return_value = mock_client
        mock_client.bucket_exists.return_value = True
        svc = MinioStorageService()
    # After the with-block, svc.client is still the mock_client object
    return svc, mock_client


@pytest.mark.unit
class TestMinioStorageService:
    def test_upload_image_calls_put_object(self):
        # Arrange
        svc, mock_client = _make_minio_service()
        file_data = b"fake image data"
        object_name = "test/receipt.jpg"

        # Act
        svc.upload_image(file_data, object_name, content_type="image/jpeg")

        # Assert
        mock_client.put_object.assert_called_once()
        args = mock_client.put_object.call_args[0]
        assert args[1] == object_name  # second positional arg is object_name

    def test_upload_image_propagates_exception(self):
        # Arrange — raise a non-S3Error exception so it isn't swallowed by the except S3Error clause
        svc, mock_client = _make_minio_service()
        mock_client.put_object.side_effect = RuntimeError("connection refused")

        # Act / Assert
        with pytest.raises(RuntimeError):
            svc.upload_image(b"data", "key")

    def test_download_image_returns_bytes(self):
        # Arrange
        svc, mock_client = _make_minio_service()
        mock_response = MagicMock()
        mock_response.read.return_value = b"image bytes"
        mock_client.get_object.return_value = mock_response

        # Act
        result = svc.download_image("test/receipt.jpg")

        # Assert
        assert result == b"image bytes"
        mock_client.get_object.assert_called_once()

    def test_get_temp_file_creates_file(self):
        # Arrange
        svc, mock_client = _make_minio_service()
        mock_response = MagicMock()
        mock_response.read.return_value = b"image bytes"
        mock_client.get_object.return_value = mock_response

        # Act
        path = svc.get_temp_file("test/receipt.jpg")

        # Assert
        assert os.path.exists(path)

        # Cleanup
        os.remove(path)


@pytest.mark.unit
class TestPusherService:
    def test_trigger_calls_pusher_client(self):
        # Arrange
        with patch("src.services.pusher_service.pusher") as mock_pusher_module:
            mock_pusher_instance = MagicMock()
            mock_pusher_module.Pusher.return_value = mock_pusher_instance
            svc = PusherService()

        # Act
        svc.trigger("receipts", "processing-done", {"id": 42})

        # Assert
        mock_pusher_instance.trigger.assert_called_once_with(
            "receipts", "processing-done", {"id": 42}
        )

    def test_trigger_no_op_when_client_is_none(self):
        # Arrange — simulate failed Pusher init
        with patch("src.services.pusher_service.pusher") as mock_pusher_module:
            mock_pusher_module.Pusher.side_effect = Exception("cannot connect")
            svc = PusherService()

        # Act — should not raise
        svc.trigger("chan", "evt", {})

        # Assert
        assert svc.client is None

    def test_trigger_swallows_exception(self):
        # Arrange
        with patch("src.services.pusher_service.pusher") as mock_pusher_module:
            mock_pusher_instance = MagicMock()
            mock_pusher_module.Pusher.return_value = mock_pusher_instance
            svc = PusherService()

        mock_pusher_instance.trigger.side_effect = RuntimeError("push failed")

        # Act — should not raise
        svc.trigger("chan", "evt", {})


@pytest.mark.unit
class TestMinioStorageServiceExtended:
    def test_upload_image_swallows_s3error(self):
        # Arrange — S3Error should be re-raised (caught + logged, then re-raised)
        with patch("src.services.minio_storage.Minio") as MockMinio:
            mock_client = MagicMock()
            MockMinio.return_value = mock_client
            mock_client.bucket_exists.return_value = True
            svc = MinioStorageService()

        mock_client.put_object.side_effect = S3Error(
            code="NoSuchBucket", message="bucket not found",
            resource="test", request_id="1", host_id="h", response=MagicMock()
        )

        # Act / Assert — S3Error is re-raised
        with pytest.raises(S3Error):
            svc.upload_image(b"data", "key/file.jpg")

    def test_download_image_reraises_s3error(self):
        # Arrange
        with patch("src.services.minio_storage.Minio") as MockMinio:
            mock_client = MagicMock()
            MockMinio.return_value = mock_client
            mock_client.bucket_exists.return_value = True
            svc = MinioStorageService()

        mock_client.get_object.side_effect = S3Error(
            code="NoSuchKey", message="key not found",
            resource="test", request_id="1", host_id="h", response=MagicMock()
        )

        # Act / Assert
        with pytest.raises(S3Error):
            svc.download_image("missing/key.jpg")

    def test_get_temp_file_no_extension_uses_png(self):
        # Arrange
        with patch("src.services.minio_storage.Minio") as MockMinio:
            mock_client = MagicMock()
            MockMinio.return_value = mock_client
            mock_client.bucket_exists.return_value = True
            svc = MinioStorageService()

        mock_response = MagicMock()
        mock_response.read.return_value = b"bytes"
        mock_client.get_object.return_value = mock_response

        # Act — object name has no extension
        path = svc.get_temp_file("receipt-no-ext")

        # Assert
        assert path.endswith(".png")
        os.remove(path)

    def test_delete_image_returns_false_on_s3error(self):
        # Arrange
        with patch("src.services.minio_storage.Minio") as MockMinio:
            mock_client = MagicMock()
            MockMinio.return_value = mock_client
            mock_client.bucket_exists.return_value = True
            svc = MinioStorageService()

        mock_client.remove_object.side_effect = S3Error(
            code="AccessDenied", message="denied",
            resource="test", request_id="1", host_id="h", response=MagicMock()
        )

        # Act
        result = svc.delete_image("key/file.jpg")

        # Assert
        assert result is False

    def test_get_presigned_url_replaces_endpoint(self):
        # Arrange
        with patch("src.services.minio_storage.Minio") as MockMinio:
            mock_client = MagicMock()
            MockMinio.return_value = mock_client
            mock_client.bucket_exists.return_value = True
            mock_client.presigned_get_object.return_value = (
                "http://minio:9000/eye-budget/receipt.jpg?X-Amz-Signature=abc"
            )
            with patch.dict(os.environ, {"MINIO_PUBLIC_ENDPOINT": "localhost:9000"}):
                svc = MinioStorageService()

            # Act
            with patch.dict(os.environ, {"MINIO_PUBLIC_ENDPOINT": "localhost:9000"}):
                url = svc.get_presigned_url("receipt.jpg")

        # Assert — internal minio:9000 replaced with localhost:9000
        assert "localhost:9000" in url
