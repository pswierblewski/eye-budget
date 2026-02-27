"""
Complete example: Processing a full transaction with both vendors and products

This script demonstrates the complete workflow:
1. Parse transaction from receipt (using OCR result)
2. Process vendor name with OpenAI API
3. Process product names with OpenAI API
4. Save everything to the database
"""

from src.data import TransactionModel
from src.services.vendors import VendorsService
from src.services.products import ProductsService
from src.repositories.vendors import VendorsRepository
from src.repositories.products import ProductsRepository
from src.db_contexts.eye_budget import EyeBudgetDbContext


def main():
    # Example transaction data (complete receipt from ALDI)
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

    print("="*70)
    print(" COMPLETE TRANSACTION PROCESSING EXAMPLE ")
    print("="*70)

    # Parse the transaction
    transaction_model = TransactionModel(**transaction_json)
    
    print(f"\nTransaction details:")
    print(f"  Date:           {transaction_model.date}")
    print(f"  Vendor:         {transaction_model.vendor}")
    print(f"  Total:          {transaction_model.total} PLN")
    print(f"  Products count: {len(transaction_model.products)}")

    # Initialize all services and repositories
    print("\n" + "-"*70)
    print("Initializing services and repositories...")
    print("-"*70)
    
    db_context = EyeBudgetDbContext()
    
    vendors_service = VendorsService()
    vendors_repository = VendorsRepository(db_context)
    
    products_service = ProductsService()
    products_repository = ProductsRepository(db_context)

    try:
        # ====================================================================
        # STEP 1: Process Vendor
        # ====================================================================
        print("\n" + "="*70)
        print(" STEP 1: PROCESSING VENDOR ")
        print("="*70)
        
        print(f"\nVendor from receipt: '{transaction_model.vendor}'")
        print("Calling OpenAI API to normalize vendor name...")
        
        vendor_mapping = vendors_service.process_vendor(transaction_model.vendor)
        
        print(f"\nVendor mapping result:")
        print(f"  Receipt name: '{vendor_mapping.vendor_alternative_name}'")
        print(f"  Normalized:   '{vendor_mapping.vendor_name}'")
        
        print("\nSaving vendor to database...")
        vendor_id = vendors_repository.process_vendor_mapping(vendor_mapping)
        
        if vendor_id:
            print(f"✓ Vendor saved with ID: {vendor_id}")
        else:
            print("✗ Failed to save vendor")

        # ====================================================================
        # STEP 2: Process Products
        # ====================================================================
        print("\n" + "="*70)
        print(" STEP 2: PROCESSING PRODUCTS ")
        print("="*70)
        
        print(f"\nProcessing {len(transaction_model.products)} products...")
        print("Calling OpenAI API to normalize product names...")
        
        product_mappings = products_service.process_products(transaction_model.products)
        
        print(f"\nProduct mappings received: {len(product_mappings.products)} items")
        print("\nFirst 5 mappings:")
        for i, mapping in enumerate(product_mappings.products[:5], 1):
            print(f"  {i}. '{mapping.product_alternative_name}'")
            print(f"     -> '{mapping.product_name}'")
        
        print("\nSaving products to database...")
        success = products_repository.process_product_mappings(product_mappings.products)
        
        if success:
            print("✓ All products saved successfully")
        else:
            print("⚠ Some products may have failed")

        # ====================================================================
        # STEP 3: Verify Data
        # ====================================================================
        print("\n" + "="*70)
        print(" STEP 3: VERIFYING DATA IN DATABASE ")
        print("="*70)
        
        # Verify vendor
        print("\nVerifying vendor...")
        queried_vendor_id = vendors_repository.get_vendor_by_alternative_name(
            transaction_model.vendor
        )
        if queried_vendor_id:
            print(f"  ✓ Vendor found: ID {queried_vendor_id}")
        else:
            print("  ✗ Vendor not found")
        
        # Verify some products
        print("\nVerifying products (first 3)...")
        for i, product in enumerate(transaction_model.products[:3], 1):
            product_id = products_repository.get_product_by_alternative_name(product.name)
            if product_id:
                print(f"  {i}. ✓ '{product.name}' -> Product ID {product_id}")
            else:
                print(f"  {i}. ✗ '{product.name}' not found")

        # ====================================================================
        # STEP 4: Summary
        # ====================================================================
        print("\n" + "="*70)
        print(" SUMMARY ")
        print("="*70)
        
        print(f"\nTransaction processed:")
        print(f"  ✓ Date:     {transaction_model.date}")
        print(f"  ✓ Vendor:   {vendor_mapping.vendor_name} (ID: {vendor_id})")
        print(f"  ✓ Products: {len(product_mappings.products)} items processed")
        print(f"  ✓ Total:    {transaction_model.total} PLN")
        
        print("\nNormalized data ready for use in your application!")
        print("\nYou can now:")
        print("  • Group transactions by normalized vendor names")
        print("  • Track purchases by normalized product names")
        print("  • Generate reports and analytics")
        print("  • Build product catalogs")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up
        print("\n" + "="*70)
        print("Cleaning up resources...")
        print("="*70)
        
        vendors_service.dispose()
        vendors_repository.dispose()
        products_service.dispose()
        products_repository.dispose()
        db_context.dispose()
        
        print("\n✓ Done!")


if __name__ == "__main__":
    main()

