# Vendors Service Integration Guide

## Overview

The Vendors Service processes receipt vendor/store names and normalizes them using OpenAI API. It maps receipt names (e.g., "ALDI Sp. z o.o.") to human-friendly names (e.g., "Aldi").

## Components

### 1. Data Models (`src/data.py`)

- **`VendorMapping`**: Represents a mapping between receipt vendor name and normalized name
  - `vendor_alternative_name`: Original receipt vendor name (e.g., "ALDI Sp. z o.o.")
  - `vendor_name`: Normalized, human-friendly name (e.g., "Aldi")

### 2. Service (`src/services/vendors.py`)

**`VendorsService`** - Handles OpenAI API integration

Key method:
```python
def process_vendor(self, vendor_name: str) -> VendorMapping
```

Takes a vendor name from a receipt and returns a normalized vendor name.

**Features:**
- Removes legal entity suffixes (Sp. z o.o., S.A., sp. j., etc.)
- Normalizes capitalization
- Keeps brand name simple and recognizable

### 3. Repository (`src/repositories/vendors.py`)

**`VendorsRepository`** - Handles database operations

Key methods:
- `get_vendor_by_name(vendor_name)`: Get vendor ID by normalized name
- `get_vendor_by_alternative_name(alternative_name)`: Get vendor ID by receipt name
- `insert_vendor(vendor_name)`: Insert new vendor
- `insert_alternative_name(alternative_name, vendor_id)`: Link receipt name to vendor
- `process_vendor_mapping(mapping)`: Process single vendor mapping and return vendor ID

### 4. Database Tables

**`vendors`** - Stores normalized vendor names
- `id` (SERIAL PRIMARY KEY)
- `name` (TEXT NOT NULL UNIQUE)

**`vendors_alternative_names`** - Stores receipt vendor names
- `id` (SERIAL PRIMARY KEY)
- `name` (TEXT NOT NULL UNIQUE) - Receipt vendor name
- `vendor` (INTEGER FK to vendors.id) - Reference to normalized vendor

## Database Setup

### Option 1: Using Migrations

Run the migration file:
```bash
psql -h $POSTGRESQL_HOST -p $POSTGRESQL_PORT -U $POSTGRESQL_USER -d $POSTGRESQL_DB -f migrations/20241010_04_vendors.sql
```

### Option 2: Manual SQL

Run the SQL from `misc/db-scripts.sql` (starting from line 274):

```sql
CREATE TABLE vendors (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE vendors_alternative_names (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    vendor INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE
);

CREATE INDEX idx_vendors_alternative_names_vendor ON vendors_alternative_names(vendor);
CREATE INDEX idx_vendors_alternative_names_name ON vendors_alternative_names(name);
```

## Usage Example

See `example_vendors_usage.py` for a complete example.

### Basic Usage

```python
from src.services.vendors import VendorsService
from src.repositories.vendors import VendorsRepository
from src.db_contexts.eye_budget import EyeBudgetDbContext

# Initialize
vendors_service = VendorsService()
db_context = EyeBudgetDbContext()
vendors_repository = VendorsRepository(db_context)

# Process vendor from transaction
vendor_mapping = vendors_service.process_vendor("ALDI Sp. z o.o.")

# Save to database and get vendor ID
vendor_id = vendors_repository.process_vendor_mapping(vendor_mapping)

# Query
vendor_id = vendors_repository.get_vendor_by_alternative_name("ALDI Sp. z o.o.")
```

## Integration with App.py

To integrate with the main application flow:

```python
# In App.__init__:
from .services.vendors import VendorsService
from .repositories.vendors import VendorsRepository

self.vendors_service = VendorsService()
self.vendors_repository = VendorsRepository(self.eye_budget_db_context)

# In App.run(), after OCR and before creating transaction:
transaction_model = TransactionModel(**ocr_result)

# Process and save vendor mapping
vendor_mapping = self.vendors_service.process_vendor(transaction_model.vendor)
vendor_id = self.vendors_repository.process_vendor_mapping(vendor_mapping)

# You can now use vendor_id in your application logic
# Continue with existing code...
transaction_id = self.my_money_repository.insert_transaction(transaction_model)
```

## Example Mappings

The LLM normalizes vendor names like this:

| Receipt Name | Normalized Name |
|--------------|----------------|
| ALDI Sp. z o.o. | Aldi |
| BIEDRONKA S.A. | Biedronka |
| KAUFLAND POLSKA MARKETY SP. Z O.O. | Kaufland |
| LIDL POLSKA SP. Z O.O. | Lidl |
| LEROY MERLIN POLSKA SP Z O O | Leroy Merlin |
| ZABKA POLSKA SP. Z O.O. | Żabka |
| CARREFOUR POLSKA SP. Z O.O. | Carrefour |

## Integration with Products Service

You can use both services together:

```python
from src.services.vendors import VendorsService
from src.services.products import ProductsService
from src.repositories.vendors import VendorsRepository
from src.repositories.products import ProductsRepository

# Initialize
vendors_service = VendorsService()
products_service = ProductsService()
vendors_repository = VendorsRepository(db_context)
products_repository = ProductsRepository(db_context)

# Process transaction
transaction_model = TransactionModel(**ocr_result)

# Process vendor
vendor_mapping = vendors_service.process_vendor(transaction_model.vendor)
vendor_id = vendors_repository.process_vendor_mapping(vendor_mapping)

# Process products
product_mappings = products_service.process_products(transaction_model.products)
products_repository.process_product_mappings(product_mappings.products)
```

## Notes

- The service removes legal entity suffixes automatically
- Duplicate alternative names are handled gracefully (ON CONFLICT DO NOTHING)
- Multiple receipt names can map to the same normalized vendor (e.g., "ALDI Sp. z o.o." and "ALDI SP Z O O" both map to "Aldi")
- Foreign key constraint ensures data integrity (CASCADE on delete)
- The `process_vendor_mapping()` method returns the vendor ID, which can be useful for further processing

