# Receipt Data Normalization System

This system normalizes receipt data (vendors and products) using OpenAI API, making it easier to track purchases, generate reports, and maintain consistent data across multiple receipts.

## Problem

Receipts contain vendor and product names in various formats:
- **Vendors**: "ALDI Sp. z o.o.", "ALDI SP Z O O", "ALDI POLSKA" → Need single representation
- **Products**: "COLGATE ADV WH CHAR75ML A", "PAPIER TOAL.4WAR10X200L A" → Hard to understand

## Solution

The system uses OpenAI API to normalize receipt data into human-friendly, consistent names:
- **Vendors**: "ALDI Sp. z o.o." → "Aldi"
- **Products**: "COLGATE ADV WH CHAR75ML A" → "Pasta do zębów"

## Architecture

```
Receipt Data (OCR)
       ↓
┌──────────────────────────────────────┐
│   VendorsService / ProductsService   │
│        (OpenAI API Integration)       │
└──────────────────────────────────────┘
       ↓
┌──────────────────────────────────────┐
│         Pydantic Models              │
│  (VendorMapping, ProductMappings)    │
└──────────────────────────────────────┘
       ↓
┌──────────────────────────────────────┐
│    Repository Layer                  │
│  (VendorsRepository, ProductsRepo)   │
└──────────────────────────────────────┘
       ↓
┌──────────────────────────────────────┐
│         PostgreSQL Database          │
│  vendors, vendors_alternative_names  │
│  products, products_alternative_names│
└──────────────────────────────────────┘
```

## Components

### 1. Data Models (`src/data.py`)
- `VendorMapping` - Maps receipt vendor name to normalized name
- `ProductMapping` - Maps receipt product name to normalized name
- `ProductMappings` - Collection of product mappings

### 2. Services
- `VendorsService` (`src/services/vendors.py`) - Normalizes vendor names
- `ProductsService` (`src/services/products.py`) - Normalizes product names

### 3. Repositories
- `VendorsRepository` (`src/repositories/vendors.py`) - Database operations for vendors
- `ProductsRepository` (`src/repositories/products.py`) - Database operations for products

### 4. Database Tables

**Vendors:**
```sql
vendors (id, name)                           -- Normalized vendor names
vendors_alternative_names (id, name, vendor) -- Receipt vendor names → vendors.id
```

**Products:**
```sql
products (id, name)                          -- Normalized product names
products_alternative_names (id, name, product) -- Receipt product names → products.id
```

## Quick Start

### 1. Setup Database

Run migrations:
```bash
psql -h $POSTGRESQL_HOST -p $POSTGRESQL_PORT -U $POSTGRESQL_USER -d $POSTGRESQL_DB \
  -f migrations/20241010_03_products.sql

psql -h $POSTGRESQL_HOST -p $POSTGRESQL_PORT -U $POSTGRESQL_USER -d $POSTGRESQL_DB \
  -f migrations/20241010_04_vendors.sql
```

Or run SQL from `misc/db-scripts.sql` (lines 257-289).

### 2. Test Services

Test vendor normalization:
```bash
python test_vendors_simple.py
```

Test product normalization:
```bash
python test_products_simple.py
```

### 3. Run Complete Example

Process a full transaction:
```bash
python example_complete_transaction.py
```

## Usage Examples

### Process Vendor Only

```python
from src.services.vendors import VendorsService
from src.repositories.vendors import VendorsRepository
from src.db_contexts.eye_budget import EyeBudgetDbContext

vendors_service = VendorsService()
db_context = EyeBudgetDbContext()
vendors_repository = VendorsRepository(db_context)

# Normalize and save
vendor_mapping = vendors_service.process_vendor("ALDI Sp. z o.o.")
vendor_id = vendors_repository.process_vendor_mapping(vendor_mapping)

print(f"Normalized: {vendor_mapping.vendor_name}")  # Output: "Aldi"
print(f"Vendor ID: {vendor_id}")
```

### Process Products Only

```python
from src.services.products import ProductsService
from src.repositories.products import ProductsRepository

products_service = ProductsService()
products_repository = ProductsRepository(db_context)

# Normalize and save
product_mappings = products_service.process_products(transaction_model.products)
products_repository.process_product_mappings(product_mappings.products)

for mapping in product_mappings.products:
    print(f"{mapping.product_alternative_name} → {mapping.product_name}")
```

### Process Complete Transaction

```python
from src.data import TransactionModel

# After OCR
transaction_model = TransactionModel(**ocr_result)

# Process vendor
vendor_mapping = vendors_service.process_vendor(transaction_model.vendor)
vendor_id = vendors_repository.process_vendor_mapping(vendor_mapping)

# Process products
product_mappings = products_service.process_products(transaction_model.products)
products_repository.process_product_mappings(product_mappings.products)
```

## Example Transformations

### Vendors

| Receipt Name | Normalized Name |
|--------------|----------------|
| ALDI Sp. z o.o. | Aldi |
| BIEDRONKA S.A. | Biedronka |
| KAUFLAND POLSKA MARKETY SP. Z O.O. | Kaufland |
| LIDL POLSKA SP. Z O.O. | Lidl |
| LEROY MERLIN POLSKA SP Z O O | Leroy Merlin |

### Products

| Receipt Name | Normalized Name |
|--------------|----------------|
| COLGATE ADV WH CHAR75ML A | Pasta do zębów |
| PAPIER TOAL.4WAR10X200L A | Papier toaletowy |
| MLEKO ŁACIĄTE 2% 1L C | Mleko |
| BANANY - KG C | Banany |
| OPUST MALINY 125G C | Rabat maliny |
| REKLAMÓWKA T-SHIRT A | Reklamówka |

## Integration with Main App

Add to `app.py`:

```python
# In App.__init__:
from .services.vendors import VendorsService
from .services.products import ProductsService
from .repositories.vendors import VendorsRepository
from .repositories.products import ProductsRepository

self.vendors_service = VendorsService()
self.vendors_repository = VendorsRepository(self.eye_budget_db_context)
self.products_service = ProductsService()
self.products_repository = ProductsRepository(self.eye_budget_db_context)

# In App.run(), after OCR:
transaction_model = TransactionModel(**ocr_result)

# Normalize vendor
vendor_mapping = self.vendors_service.process_vendor(transaction_model.vendor)
vendor_id = self.vendors_repository.process_vendor_mapping(vendor_mapping)

# Normalize products
product_mappings = self.products_service.process_products(transaction_model.products)
self.products_repository.process_product_mappings(product_mappings.products)

# Continue with existing code...
transaction_id = self.my_money_repository.insert_transaction(transaction_model)
```

## Benefits

1. **Consistent Data**: Same vendor/product always has same name
2. **Easy Querying**: Find all purchases from "Aldi" instead of multiple variations
3. **Better Reports**: Group by normalized names for accurate analytics
4. **Automatic Learning**: New receipt variations automatically linked to existing vendors/products
5. **Human-Readable**: Normalized names are clear and understandable

## Files

### Implementation
- `src/data.py` - Pydantic models
- `src/services/vendors.py` - Vendor normalization service
- `src/services/products.py` - Product normalization service
- `src/repositories/vendors.py` - Vendor database operations
- `src/repositories/products.py` - Product database operations

### Database
- `migrations/20241010_03_products.sql` - Products tables migration
- `migrations/20241010_04_vendors.sql` - Vendors tables migration
- `misc/db-scripts.sql` - All SQL scripts

### Examples & Tests
- `test_vendors_simple.py` - Test vendor normalization
- `test_products_simple.py` - Test product normalization
- `example_vendors_usage.py` - Vendor complete example
- `example_products_usage.py` - Product complete example
- `example_complete_transaction.py` - Full transaction example

### Documentation
- `VENDORS_INTEGRATION_GUIDE.md` - Vendor service guide
- `PRODUCTS_INTEGRATION_GUIDE.md` - Product service guide
- `README_NORMALIZATION.md` - This file

## Notes

- Services use OpenAI API (requires valid API key)
- Duplicate handling: ON CONFLICT DO NOTHING (safe to run multiple times)
- Foreign keys ensure data integrity (CASCADE on delete)
- Indexes optimize query performance
- All components follow repository pattern for clean architecture

