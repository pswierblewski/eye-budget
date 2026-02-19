# Ground Truth Evaluation Guide

The ground truth evaluation system lets you build a dataset of verified receipt data and measure OCR accuracy over time. The idea is model-assisted labeling: the model produces a first draft, you correct any errors, and the corrected data becomes the reference for future evaluation runs.

## Workflow Overview

1. Upload a receipt image
2. Review the OCR result
3. Correct any errors
4. Repeat for more receipts to build the dataset
5. Run evaluation to measure accuracy against the ground truth

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ground-truth` | Upload receipt image, run OCR, store as ground truth |
| GET | `/ground-truth` | List all ground truth entries |
| GET | `/ground-truth/{id}` | Get a single ground truth entry |
| PUT | `/ground-truth/{id}` | Update ground truth with corrections |
| POST | `/receipts/evaluate` | Run evaluation against all ground truth entries |

## Step-by-step

### 1. Upload a receipt

```bash
curl -X POST "http://localhost:8000/ground-truth" \
  -F "file=@/path/to/receipt.png"
```

Response:

```json
{
  "id": 1,
  "filename": "receipt.png",
  "ground_truth": {
    "vendor": "BIEDRONKA",
    "title": "PARAGON FISKALNY",
    "date": "2024-01-15",
    "total": 45.67,
    "products": [
      { "name": "MLEKO 3.2%", "quantity": 2, "price": 5.98, "unit_price": 2.99 },
      { "name": "CHLEB PSZENNY", "quantity": 1, "price": 3.49, "unit_price": 3.49 }
    ]
  }
}
```

### 2. Review the result

Check the response JSON. If everything is correct, you're done with this entry. If not, proceed to step 3.

### 3. Correct errors

Take the JSON from step 1, fix any mistakes, and send it back:

```bash
curl -X PUT "http://localhost:8000/ground-truth/1" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor": "Biedronka",
    "title": "PARAGON FISKALNY",
    "date": "2024-01-15",
    "total": 45.67,
    "products": [
      { "name": "Mleko 3.2%", "quantity": 2, "price": 5.98, "unit_price": 2.99 },
      { "name": "Chleb pszenny", "quantity": 1, "price": 3.49, "unit_price": 3.49 }
    ]
  }'
```

The full `TransactionModel` schema is required in the PUT body:

| Field | Type | Description |
|-------|------|-------------|
| `vendor` | string | Store name |
| `title` | string | Document title (e.g., "PARAGON FISKALNY") |
| `date` | string | Transaction date |
| `total` | float | Total amount |
| `products` | array | List of products |
| `products[].name` | string | Product name |
| `products[].quantity` | float | Quantity purchased |
| `products[].price` | float | Total price for this line |
| `products[].unit_price` | float or null | Price per single unit |

### 4. Build the dataset

Repeat steps 1-3 for more receipts. The more entries you have, the more meaningful the evaluation metrics will be.

List all entries at any time:

```bash
curl "http://localhost:8000/ground-truth"
```

Get a specific entry:

```bash
curl "http://localhost:8000/ground-truth/1"
```

### 5. Run evaluation

Once you have ground truth entries, run an evaluation:

```bash
curl -X POST "http://localhost:8000/receipts/evaluate"
```

This will:
- Download each ground truth image from MinIO
- Re-run OCR on it (using the current model and config)
- Compare the fresh OCR result to the stored ground truth
- Return detailed metrics

## Evaluation Metrics

### Per-file metrics

| Metric | Description |
|--------|-------------|
| `vendor_correct` | Does extracted vendor match ground truth (case-insensitive) |
| `date_correct` | Does extracted date match exactly |
| `total_correct` | Is extracted total within 0.01 of ground truth |
| `total_accuracy` | `1.0 - (abs(extracted - expected) / expected)` |
| `product_count_correct` | Same number of products |
| `products_accuracy` | Fraction of ground truth products matched by name and price |
| `is_consistent` | Does the sum of product prices match the extracted total |
| `processing_time_ms` | Time to process the receipt |

### Run summary metrics

| Metric | Description |
|--------|-------------|
| `success_rate` | Fraction of files processed without errors |
| `avg_vendor_accuracy` | Percentage of correct vendor extractions |
| `avg_date_accuracy` | Percentage of correct date extractions |
| `avg_total_accuracy` | Average total accuracy across all files |
| `avg_products_accuracy` | Average products accuracy across all files |
| `avg_processing_time_ms` | Average processing time per file |
| `avg_field_completeness` | Average fraction of fields that were extracted |
| `avg_consistency_rate` | Percentage of files with internally consistent totals |

## Typical use case

After changing the OCR model, prompt, or preprocessing config, re-run the evaluation to see if accuracy improved:

```bash
# Run evaluation with current config
curl -X POST "http://localhost:8000/receipts/evaluate" | python -m json.tool

# Change the MODEL env var, restart the server, then re-run
curl -X POST "http://localhost:8000/receipts/evaluate" | python -m json.tool

# Compare the two runs in the evaluation_runs table
```

Each evaluation run is stored in the `evaluation_runs` and `evaluation_results` database tables, so you can query historical results directly in PostgreSQL.
