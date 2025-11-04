#!/usr/bin/env python3
"""
Setup Stripe products and prices for VeritasLogic subscription plans.
Run this once to create products in Stripe dashboard, then update pricing_config.py with the returned IDs.
"""
import os
import stripe
from shared.pricing_config import SUBSCRIPTION_PLANS

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def create_stripe_products():
    """Create Stripe products and prices for all subscription plans"""
    
    print("=" * 80)
    print("Creating Stripe Products and Prices for VeritasLogic Subscriptions")
    print("=" * 80)
    print()
    
    results = {}
    
    for plan_key, plan_config in SUBSCRIPTION_PLANS.items():
        if plan_key == 'trial':
            print(f"⏭️  Skipping trial plan (not a paid subscription)\n")
            continue
        
        print(f"Creating product: {plan_config['name']}")
        print(f"  Price: ${plan_config['price_monthly']}/month")
        print(f"  Words: {plan_config['word_allowance']:,}")
        
        try:
            # Create product
            product = stripe.Product.create(
                name=f"VeritasLogic {plan_config['name']}",
                description=f"{plan_config['description']} - {plan_config['word_allowance']:,} words/month",
                metadata={
                    'plan_key': plan_key,
                    'word_allowance': plan_config['word_allowance'],
                    'platform': 'veritaslogic.ai'
                }
            )
            
            print(f"  ✅ Product created: {product.id}")
            
            # Create price (monthly recurring)
            price = stripe.Price.create(
                product=product.id,
                unit_amount=int(plan_config['price_monthly'] * 100),  # Convert to cents
                currency='usd',
                recurring={
                    'interval': 'month',
                    'interval_count': 1,
                    'trial_period_days': 14
                },
                metadata={
                    'plan_key': plan_key,
                    'word_allowance': plan_config['word_allowance']
                }
            )
            
            print(f"  ✅ Price created: {price.id}")
            print()
            
            results[plan_key] = {
                'product_id': product.id,
                'price_id': price.id,
                'name': plan_config['name'],
                'price_monthly': plan_config['price_monthly'],
                'word_allowance': plan_config['word_allowance']
            }
            
        except stripe.error.StripeError as e:
            print(f"  ❌ Error creating {plan_key}: {e}")
            print()
    
    print("=" * 80)
    print("RESULTS - Copy these price IDs to pricing_config.py")
    print("=" * 80)
    print()
    
    for plan_key, data in results.items():
        print(f"{plan_key.upper()}:")
        print(f"  Product ID:  {data['product_id']}")
        print(f"  Price ID:    {data['price_id']}")
        print(f"  Name:        {data['name']}")
        print(f"  Price:       ${data['price_monthly']}/month")
        print(f"  Words:       {data['word_allowance']:,}")
        print()
    
    print("=" * 80)
    print("UPDATE pricing_config.py WITH THESE VALUES:")
    print("=" * 80)
    print()
    print("SUBSCRIPTION_PLANS = {")
    for plan_key, data in results.items():
        print(f"    '{plan_key}': {{")
        print(f"        ...,  # Keep existing config")
        print(f"        'stripe_product_id': '{data['product_id']}',")
        print(f"        'stripe_price_id': '{data['price_id']}',")
        print(f"    }},")
    print("}")
    print()
    
    return results

def list_existing_products():
    """List existing Stripe products for reference"""
    print("=" * 80)
    print("Existing Stripe Products")
    print("=" * 80)
    print()
    
    try:
        products = stripe.Product.list(limit=100, active=True)
        
        if not products.data:
            print("No active products found in Stripe account.")
            print()
            return
        
        for product in products.data:
            print(f"Product: {product.name}")
            print(f"  ID: {product.id}")
            
            # Get prices for this product
            prices = stripe.Price.list(product=product.id, active=True)
            for price in prices.data:
                amount = price.unit_amount / 100 if price.unit_amount else 0
                interval = price.recurring.get('interval') if price.recurring else 'one-time'
                trial_days = price.recurring.get('trial_period_days') if price.recurring else 0
                
                print(f"  Price: {price.id} - ${amount:.2f}/{interval}")
                if trial_days:
                    print(f"    Trial: {trial_days} days")
            print()
        
    except stripe.error.StripeError as e:
        print(f"Error listing products: {e}")
        print()

if __name__ == '__main__':
    import sys
    
    if not os.getenv('STRIPE_SECRET_KEY'):
        print("ERROR: STRIPE_SECRET_KEY environment variable not set")
        sys.exit(1)
    
    print()
    print("VeritasLogic Stripe Product Setup")
    print()
    
    # Check for existing products first
    list_existing_products()
    
    # Confirm before creating
    response = input("Create new products and prices? This will create charges in Stripe. [y/N]: ")
    
    if response.lower() == 'y':
        results = create_stripe_products()
        
        print()
        print("✅ Setup complete!")
        print()
        print("Next steps:")
        print("1. Copy the price IDs above to pricing_config.py")
        print("2. Restart the backend API workflow")
        print("3. Test the /api/subscription/upgrade endpoint")
        print()
    else:
        print("Cancelled. No changes made to Stripe.")
