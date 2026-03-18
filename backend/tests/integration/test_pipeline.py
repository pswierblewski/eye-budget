import os
import tempfile
import pytest
import psycopg2
from unittest.mock import MagicMock, patch


def ocr_mock_result(vendor="Test Store", date="2024-06-15", total=49.99):
    """Return a minimal valid OCR result dict."""
    return {
        "vendor": vendor,
        "title": "PARAGON FISKALNY",
        "products": [
            {
                "name": "Mleko",
                "quantity": 1.0,
                "price": 3.99,
                "unit_price": 3.99,
            }
        ],
        "total": total,
        "date": date,
    }


def _mock_pipeline_services(app, ocr_result):
    """Mock all LLM/file-system services; keep real DB and MinIO."""
    # Create a real temp file so MinIO upload doesn't fail
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # minimal JPEG header
    tmp.close()

    app.preprocessing_service = MagicMock()
    app.preprocessing_service.preprocess_image.return_value = tmp.name

    app.ocr_service = MagicMock()
    app.ocr_service.process_image.return_value = ocr_result

    # vendors_service returns a mapping with the same vendor name
    vendor_mapping = MagicMock()
    vendor_mapping.vendor_name = ocr_result["vendor"]
    app.vendors_service = MagicMock()
    app.vendors_service.process_vendor.return_value = vendor_mapping

    # products_service returns empty mappings
    from src.data import ProductMappings
    app.products_service = MagicMock()
    app.products_service.process_products.return_value = ProductMappings(products=[])

    # categories_service returns empty candidates
    app.categories_service = MagicMock()
    app.categories_service.assign_category_candidates.return_value = {}

    # text_localization_service — skip
    app.text_localization_service = MagicMock()

    return tmp.name


@pytest.mark.integration
def test_process_single_file_success(integration_app, migrated_db):
    app = integration_app
    filename = "test_receipt_001.jpg"

    ocr_result = ocr_mock_result()
    tmp_path = _mock_pipeline_services(app, ocr_result)

    try:
        # Add receipt row to DB first
        app.receipts_scans_repository.add_receipt(filename)

        # Process the file
        success = app._process_single_file(filename)
        assert success is True

        # Query DB directly to verify status is PROCESSED
        pg = migrated_db
        conn = psycopg2.connect(
            host=pg.get_container_host_ip(),
            port=pg.get_exposed_port(5432),
            dbname=pg.dbname,
            user=pg.username,
            password=pg.password,
        )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, result FROM receipts_scans WHERE filename = %s",
                (filename,),
            )
            row = cur.fetchone()
        conn.close()

        assert row is not None
        # _process_single_file sets status to 'processed', then set_category_candidates
        # updates it to 'to_confirm' — both indicate successful processing
        assert row[0] in ("processed", "to_confirm")
        assert row[1] is not None
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@pytest.mark.integration
def test_process_single_file_ocr_failure(integration_app, migrated_db):
    app = integration_app
    filename = "test_receipt_002.jpg"

    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    tmp.close()

    app.preprocessing_service = MagicMock()
    app.preprocessing_service.preprocess_image.return_value = tmp.name
    app.ocr_service = MagicMock()
    app.ocr_service.process_image.side_effect = RuntimeError("OCR failed")

    try:
        app.receipts_scans_repository.add_receipt(filename)
        success = app._process_single_file(filename)
        assert success is False

        pg = migrated_db
        conn = psycopg2.connect(
            host=pg.get_container_host_ip(),
            port=pg.get_exposed_port(5432),
            dbname=pg.dbname,
            user=pg.username,
            password=pg.password,
        )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, message FROM receipts_scans WHERE filename = %s",
                (filename,),
            )
            row = cur.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "failed"
        assert row[1] is not None
        assert "OCR failed" in row[1]
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


@pytest.mark.integration
def test_confirm_receipt_persists_transaction(integration_app, migrated_db):
    app = integration_app
    filename = "test_receipt_003.jpg"

    ocr_result = ocr_mock_result(vendor="Biedronka", total=25.50)
    tmp_path = _mock_pipeline_services(app, ocr_result)

    try:
        # Full pipeline: add → process (with mocked OCR) → confirm
        app.receipts_scans_repository.add_receipt(filename)
        app._process_single_file(filename)

        scan_id = app.receipts_scans_repository.get_scan_id_by_filename(filename)
        assert scan_id is not None

        # Set status to TO_CONFIRM so confirm_receipt can proceed
        app.receipts_scans_repository.set_status_to_confirm_by_id(scan_id)

        # Need a valid category in DB (category_group_id removed by migration)
        pg = migrated_db
        conn = psycopg2.connect(
            host=pg.get_container_host_ip(),
            port=pg.get_exposed_port(5432),
            dbname=pg.dbname,
            user=pg.username,
            password=pg.password,
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO categories (name) VALUES ('Food') RETURNING id"
            )
            category_id = cur.fetchone()[0]
        conn.close()

        from src.data import ConfirmReceiptRequest
        request = ConfirmReceiptRequest(
            product_categories={"Mleko": category_id},
        )

        app.confirm_receipt(scan_id, request)

        # Verify a receipt_transactions row exists
        conn = psycopg2.connect(
            host=pg.get_container_host_ip(),
            port=pg.get_exposed_port(5432),
            dbname=pg.dbname,
            user=pg.username,
            password=pg.password,
        )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT total FROM receipt_transactions WHERE scan_id = %s",
                (scan_id,),
            )
            row = cur.fetchone()
        conn.close()

        assert row is not None
        assert abs(float(row[0]) - 25.50) < 0.01
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
