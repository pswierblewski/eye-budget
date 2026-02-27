"""
Simple test to verify VendorsService without database
This demonstrates the OpenAI API integration for vendor normalization
"""

from src.services.vendors import VendorsService


def main():
    print("="*60)
    print("Testing VendorsService (OpenAI API Integration)")
    print("="*60)
    
    # Sample vendor names from receipts
    sample_vendors = [
        "ALDI Sp. z o.o.",
        "BIEDRONKA S.A.",
        "KAUFLAND POLSKA MARKETY SP. Z O.O.",
        "LIDL POLSKA SP. Z O.O.",
        "LEROY MERLIN POLSKA SP Z O O",
    ]
    
    print("\nInput vendors (from receipts):")
    for i, vendor in enumerate(sample_vendors, 1):
        print(f"  {i}. {vendor}")
    
    # Initialize service
    print("\nInitializing VendorsService...")
    vendors_service = VendorsService()
    
    try:
        print("\n" + "="*60)
        print("Processing vendors with OpenAI API...")
        print("="*60)
        
        # Process each vendor
        for i, vendor in enumerate(sample_vendors, 1):
            print(f"\n{i}. Processing: {vendor}")
            vendor_mapping = vendors_service.process_vendor(vendor)
            print(f"   Receipt name: {vendor_mapping.vendor_alternative_name}")
            print(f"   Normalized:   {vendor_mapping.vendor_name}")
        
        print("\n" + "="*60)
        print("✓ Test completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        vendors_service.dispose()


if __name__ == "__main__":
    main()

