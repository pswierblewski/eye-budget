"""
Simple test to verify ProductsService without database
This demonstrates the OpenAI API integration
"""

from src.data import ProductItem
from src.services.products import ProductsService


def main():
    print("="*60)
    print("Testing ProductsService (OpenAI API Integration)")
    print("="*60)
    
    # Create sample products from a receipt
    sample_products = [
        ProductItem(name="PAPIER TOAL.4WAR10X200L A", price=24.99, quantity=1, unit_price=24.99),
        ProductItem(name="COLGATE ADV WH CHAR75ML A", price=9.99, quantity=1, unit_price=9.99),
        ProductItem(name="MLEKO ŁACIĄTE 2% 1L C", price=51.48, quantity=12, unit_price=4.29),
        ProductItem(name="BANANY - KG C", price=4.66, quantity=0.666, unit_price=6.99),
        ProductItem(name="REKLAMÓWKA T-SHIRT A", price=0.89, quantity=1, unit_price=0.89),
    ]
    
    print("\nInput products (from receipt):")
    for i, product in enumerate(sample_products, 1):
        print(f"  {i}. {product.name}")
    
    # Initialize service
    print("\nInitializing ProductsService...")
    products_service = ProductsService()
    
    try:
        # Process products
        print("\nCalling OpenAI API to normalize product names...")
        product_mappings = products_service.process_products(sample_products)
        
        # Display results
        print("\n" + "="*60)
        print("Results:")
        print("="*60)
        for i, mapping in enumerate(product_mappings.products, 1):
            print(f"\n{i}. Receipt name: {mapping.product_alternative_name}")
            print(f"   Normalized:   {mapping.product_name}")
        
        print("\n" + "="*60)
        print("✓ Test completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        products_service.dispose()


if __name__ == "__main__":
    main()


