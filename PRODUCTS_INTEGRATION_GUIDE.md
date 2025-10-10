# Products Service Integration Guide

## Overview

The Products Service processes receipt product names and normalizes them using OpenAI API. It maps receipt names (e.g., "COLGATE ADV WH CHAR75ML A") to human-friendly names (e.g., "Pasta do zębów").

## Components

### 1. Data Models (`src/data.py`)

- **`ProductMapping`**: Represents a single mapping between receipt name and normalized name
  - `product_alternative_name`: Original receipt product name
  - `product_name`: Normalized, human-friendly name

- **`ProductMappings`**: List of product mappings
  - `products`: List of `ProductMapping` objects

### 2. Service (`src/services/products.py`)

**`ProductsService`** - Handles OpenAI API integration

Key method:
```python
def process_products(self, products: List[ProductItem]) -> ProductMappings
```

Takes a list of `ProductItem` objects from a receipt and returns normalized product names.

### 3. Repository (`src/repositories/products.py`)

**`ProductsRepository`** - Handles database operations

Key methods:
- `get_product_by_name(product_name)`: Get product ID by normalized name
- `get_product_by_alternative_name(alternative_name)`: Get product ID by receipt name
- `insert_product(product_name)`: Insert new product
- `insert_alternative_name(alternative_name, product_id)`: Link receipt name to product
- `process_product_mappings(mappings)`: Process entire list of mappings

### 4. Database Tables

**`products`** - Stores normalized product names
- `id` (SERIAL PRIMARY KEY)
- `name` (TEXT NOT NULL UNIQUE)

**`products_alternative_names`** - Stores receipt product names
- `id` (SERIAL PRIMARY KEY)
- `name` (TEXT NOT NULL UNIQUE) - Receipt product name
- `product` (INTEGER FK to products.id) - Reference to normalized product

## Database Setup

Run the SQL script from `misc/db-scripts.sql` (starting from line 257) to create the tables:

```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE products_alternative_names (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    product INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX idx_products_alternative_names_product ON products_alternative_names(product);
CREATE INDEX idx_products_alternative_names_name ON products_alternative_names(name);
```

## Usage Example

See `example_products_usage.py` for a complete example.

### Basic Usage

```python
from src.data import TransactionModel
from src.services.products import ProductsService
from src.repositories.products import ProductsRepository
from src.db_contexts.eye_budget import EyeBudgetDbContext

# Initialize
products_service = ProductsService()
db_context = EyeBudgetDbContext()
products_repository = ProductsRepository(db_context)

# Process products from transaction
transaction_model = TransactionModel(**transaction_json)
product_mappings = products_service.process_products(transaction_model.products)

# Save to database
products_repository.process_product_mappings(product_mappings.products)

# Query
product_id = products_repository.get_product_by_alternative_name("COLGATE ADV WH CHAR75ML A")
```

## Integration with App.py

To integrate with the main application flow, you can add this after OCR processing:

```python
# In App.__init__:
from .services.products import ProductsService
from .repositories.products import ProductsRepository

self.products_service = ProductsService()
self.products_repository = ProductsRepository(self.eye_budget_db_context)

# In App.run(), after creating transaction_model:
transaction_model = TransactionModel(**ocr_result)

# Process and save product mappings
product_mappings = self.products_service.process_products(transaction_model.products)
self.products_repository.process_product_mappings(product_mappings.products)

# Continue with existing code...
transaction_id = self.my_money_repository.insert_transaction(transaction_model)
```

## Example Mappings

The LLM normalizes product names like this:

| Receipt Name | Normalized Name |
|--------------|----------------|
| COLGATE ADV WH CHAR75ML A | Pasta do zębów |
| PAPIER TOAL.4WAR10X200L A | Papier toaletowy |
| MLEKO ŁACIĄTE 2% 1L C | Mleko |
| BANANY - KG C | Banany |
| OPUST MALINY 125G C | Rabat maliny |
| REKLAMÓWKA T-SHIRT A | Reklamówka |

## Notes

- The service removes brands, weights, and volumes unless essential
- Duplicate alternative names are handled gracefully (ON CONFLICT DO NOTHING)
- Multiple receipt names can map to the same normalized product
- Foreign key constraint ensures data integrity (CASCADE on delete)


