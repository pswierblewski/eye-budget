"""
Example usage of ProductsService and ProductsRepository

This script demonstrates how to:
1. Process product names from a receipt using OpenAI API
2. Save the normalized products and their alternative names to the database
"""

import json
from src.data import TransactionModel
from src.services.products import ProductsService
from src.repositories.products import ProductsRepository
from src.db_contexts.eye_budget import EyeBudgetDbContext


def main():
    # Example transaction data (the same from your request)
    transaction_json = {
        "date": "2025-07-17",
        "title": "PARAGON FISKALNY",
        "total": 196.14,
        "vendor": "ALDI Sp. z o.o.",
        "products": [
            {"name": "PAPIER TOAL.4WAR10X200L A", "price": 24.99, "quantity": 1, "unit_price": 24.99},
            {"name": "RECZ.KUCH.3W 2X100 LIST A", "price": 19.98, "quantity": 2, "unit_price": 9.99},
            {"name": "ŻYW.ZDR.WOD DEL.MU.1.5L A", "price": 48.42, "quantity": 18, "unit_price": 2.69},
            {"name": "MLEKO ŁACIĄTE 2% 1L C", "price": 51.48, "quantity": 12, "unit_price": 4.29},
            {"name": "REKLAMÓWKA T-SHIRT A", "price": 0.89, "quantity": 1, "unit_price": 0.89},
            {"name": "ZMYWAK WIELOFUN. 6 SZT. A", "price": 3.99, "quantity": 1, "unit_price": 3.99},
            {"name": "COLGATE ADV WH CHAR75ML A", "price": 9.99, "quantity": 1, "unit_price": 9.99},
            {"name": "FOLIA SPOŻYWCZA 75M A", "price": 7.49, "quantity": 1, "unit_price": 7.49},
            {"name": "BUŁKA PARYSKA 240G C", "price": 2.99, "quantity": 1, "unit_price": 2.99},
            {"name": "MALINY 125G C", "price": 9.99, "quantity": 1, "unit_price": 9.99},
            {"name": "OPUST MALINY 125G C", "price": -3.0, "quantity": 1, "unit_price": -3.0},
            {"name": "POLSKIE TRUSKAWKI 500G C", "price": 14.99, "quantity": 1, "unit_price": 14.99},
            {"name": "OPUST POLSKIE TRUSKAWKI 500G C", "price": -4.5, "quantity": 1, "unit_price": -4.5},
            {"name": "ROGAL 100G C", "price": 3.78, "quantity": 2, "unit_price": 1.89},
            {"name": "BANANY - KG C", "price": 4.66, "quantity": 0.666, "unit_price": 6.99}
        ]
    }

    # Parse the transaction
    transaction_model = TransactionModel(**transaction_json)

    # Initialize services and repositories
    print("Initializing services...")
    products_service = ProductsService()
    db_context = EyeBudgetDbContext()
    products_repository = ProductsRepository(db_context)

    try:
        # Step 1: Process products with OpenAI API
        print("\n" + "="*60)
        print("Step 1: Processing products with OpenAI API...")
        print("="*60)
        
        product_mappings = products_service.process_products(transaction_model.products)
        
        print(f"\nReceived {len(product_mappings.products)} product mappings:")
        for mapping in product_mappings.products:
            print(f"  • '{mapping.product_alternative_name}' -> '{mapping.product_name}'")

        # Step 2: Save to database
        print("\n" + "="*60)
        print("Step 2: Saving to database...")
        print("="*60)
        
        success = products_repository.process_product_mappings(product_mappings.products)
        
        if success:
            print("\n✓ All product mappings processed successfully!")
        else:
            print("\n⚠ Some product mappings failed to process.")

        # Step 3: Verify by querying the database
        print("\n" + "="*60)
        print("Step 3: Verifying data in database...")
        print("="*60)
        
        for mapping in product_mappings.products[:3]:  # Just check first 3 for brevity
            product_id = products_repository.get_product_by_alternative_name(
                mapping.product_alternative_name
            )
            if product_id:
                print(f"  ✓ '{mapping.product_alternative_name}' -> Product ID: {product_id}")
            else:
                print(f"  ✗ '{mapping.product_alternative_name}' not found")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up
        print("\n" + "="*60)
        print("Cleaning up resources...")
        print("="*60)
        products_service.dispose()
        products_repository.dispose()
        db_context.dispose()
        print("\n✓ Done!")


if __name__ == "__main__":
    main()


