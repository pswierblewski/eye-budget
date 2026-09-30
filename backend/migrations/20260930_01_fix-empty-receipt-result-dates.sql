-- Empty string in result.date breaks (""::date) in unified transaction queries.

UPDATE receipts_scans
SET result = jsonb_set(
    result,
    '{date}',
    to_jsonb(
        to_char(
            to_date(substring(filename FROM 'Scanned_([0-9]{8})'), 'YYYYMMDD'),
            'YYYY-MM-DD'
        )
    )
)
WHERE TRIM(COALESCE(result->>'date', '')) = ''
  AND filename ~ '^Scanned_[0-9]{8}_';

UPDATE receipts_scans
SET result = result - 'date'
WHERE TRIM(COALESCE(result->>'date', '')) = '';

UPDATE receipt_transactions rt
SET date = (rs.result->>'date')::date
FROM receipts_scans rs
WHERE rt.scan_id = rs.id
  AND rt.date IS NULL
  AND rs.result ? 'date'
  AND rs.result->>'date' ~ '^\d{4}-\d{2}-\d{2}$';
