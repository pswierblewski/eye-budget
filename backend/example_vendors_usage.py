"""
Example usage of VendorsService and VendorsRepository

This script demonstrates how to:
1. Process vendor name from a receipt using OpenAI API
2. Save the normalized vendor and its alternative name to the database
"""

from src.data import TransactionModel
from src.services.vendors import VendorsService
from src.repositories.vendors import VendorsRepository
from src.db_contexts.eye_budget import EyeBudgetDbContext


def main():
    # Example transaction data
    transaction_json = {
        "date": "2025-07-17",
        "title": "PARAGON FISKALNY",
        "total": 196.14,
        "vendor": "ALDI Sp. z o.o.",
        "products": [
            {"name": "PAPIER TOAL.4WAR10X200L A", "price": 24.99, "quantity": 1, "unit_price": 24.99},
            {"name": "MLEKO ŁACIĄTE 2% 1L C", "price": 51.48, "quantity": 12, "unit_price": 4.29},
        ]
    }

    # Parse the transaction
    transaction_model = TransactionModel(**transaction_json)

    # Initialize services and repositories
    print("Initializing services...")
    vendors_service = VendorsService()
    db_context = EyeBudgetDbContext()
    vendors_repository = VendorsRepository(db_context)

    try:
        # Step 1: Process vendor with OpenAI API
        print("\n" + "="*60)
        print("Step 1: Processing vendor with OpenAI API...")
        print("="*60)
        
        print(f"\nVendor from receipt: {transaction_model.vendor}")
        vendor_mapping = vendors_service.process_vendor(transaction_model.vendor)
        
        print(f"\nVendor mapping:")
        print(f"  • Receipt name: '{vendor_mapping.vendor_alternative_name}'")
        print(f"  • Normalized:   '{vendor_mapping.vendor_name}'")

        # Step 2: Save to database
        print("\n" + "="*60)
        print("Step 2: Saving to database...")
        print("="*60)
        
        vendor_id = vendors_repository.process_vendor_mapping(vendor_mapping)
        
        if vendor_id:
            print(f"\n✓ Vendor mapping processed successfully! Vendor ID: {vendor_id}")
        else:
            print("\n⚠ Failed to process vendor mapping.")

        # Step 3: Verify by querying the database
        print("\n" + "="*60)
        print("Step 3: Verifying data in database...")
        print("="*60)
        
        # Query by alternative name
        queried_id = vendors_repository.get_vendor_by_alternative_name(
            vendor_mapping.vendor_alternative_name
        )
        if queried_id:
            print(f"  ✓ Query by alternative name: '{vendor_mapping.vendor_alternative_name}' -> Vendor ID: {queried_id}")
        
        # Query by normalized name
        queried_id = vendors_repository.get_vendor_by_name(vendor_mapping.vendor_name)
        if queried_id:
            print(f"  ✓ Query by normalized name: '{vendor_mapping.vendor_name}' -> Vendor ID: {queried_id}")

        # Step 4: Test with another alternative name for the same vendor
        print("\n" + "="*60)
        print("Step 4: Testing with another alternative name...")
        print("="*60)
        
        # Simulate another receipt from the same vendor with slightly different name
        another_alternative = "ALDI SP Z O O"
        print(f"\nProcessing: {another_alternative}")
        vendor_mapping2 = vendors_service.process_vendor(another_alternative)
        
        print(f"Normalized to: '{vendor_mapping2.vendor_name}'")
        
        # This should link to the existing vendor if LLM returns the same normalized name
        vendor_id2 = vendors_repository.process_vendor_mapping(vendor_mapping2)
        print(f"Vendor ID: {vendor_id2}")
        
        if vendor_id == vendor_id2:
            print(f"✓ Both alternative names correctly mapped to the same vendor (ID: {vendor_id})")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up
        print("\n" + "="*60)
        print("Cleaning up resources...")
        print("="*60)
        vendors_service.dispose()
        vendors_repository.dispose()
        db_context.dispose()
        print("\n✓ Done!")


if __name__ == "__main__":
    main()

