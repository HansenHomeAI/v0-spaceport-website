#!/usr/bin/env python3
"""
Stripe Products and Prices Setup Script
Automatically creates products and prices for Spaceport subscription plans
"""

import os
import stripe
import sys
from typing import Dict, Any

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Plan configurations
PLANS = {
    'single': {
        'name': 'Single Model',
        'description': 'One active 3D model with premium features',
        'price': 2900,  # $29.00 in cents
        'metadata': {
            'plan_type': 'single',
            'max_models': '1',
            'support_level': 'email',
            'trial_days': '0'
        }
    },
    'starter': {
        'name': 'Starter',
        'description': 'Up to five active 3D models',
        'price': 9900,  # $99.00 in cents
        'metadata': {
            'plan_type': 'starter',
            'max_models': '5',
            'support_level': 'priority',
            'trial_days': '0'
        }
    },
    'growth': {
        'name': 'Growth',
        'description': 'Up to twenty active 3D models',
        'price': 29900,  # $299.00 in cents
        'metadata': {
            'plan_type': 'growth',
            'max_models': '20',
            'support_level': 'dedicated',
            'trial_days': '0'
        }
    }
}

def create_product(plan_key: str, plan_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create a Stripe product"""
    try:
        print(f"Creating product: {plan_config['name']}")
        
        product = stripe.Product.create(
            name=plan_config['name'],
            description=plan_config['description'],
            metadata=plan_config['metadata']
        )
        
        print(f"✅ Product created: {product.id}")
        return product
        
    except Exception as e:
        print(f"❌ Error creating product {plan_config['name']}: {str(e)}")
        return None

def create_price(product_id: str, plan_key: str, plan_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create a Stripe price for a product"""
    try:
        print(f"Creating price for {plan_config['name']}: ${plan_config['price']/100}/month")
        
        price = stripe.Price.create(
            product=product_id,
            unit_amount=plan_config['price'],
            currency='usd',
            recurring={'interval': 'month'},
            metadata={
                'plan_type': plan_key,
                'max_models': plan_config['metadata']['max_models'],
                'support_level': plan_config['metadata']['support_level']
            }
        )
        
        print(f"✅ Price created: {price.id}")
        return price
        
    except Exception as e:
        print(f"❌ Error creating price for {plan_config['name']}: {str(e)}")
        return None

def main():
    """Main execution function"""
    print("🚀 Setting up Stripe products and prices for Spaceport...")
    print("=" * 60)
    
    # Check if Stripe key is set
    if not stripe.api_key:
        print("❌ Error: STRIPE_SECRET_KEY environment variable not set")
        print("Please set your Stripe secret key and run again")
        sys.exit(1)
    
    # Test Stripe connection
    try:
        stripe.Account.retrieve()
        print("✅ Stripe connection successful")
    except Exception as e:
        print(f"❌ Error connecting to Stripe: {str(e)}")
        sys.exit(1)
    
    print()
    
    # Store results
    results = {}
    
    # Create products and prices
    for plan_key, plan_config in PLANS.items():
        print(f"\n📦 Processing {plan_key.upper()} plan...")
        
        # Create product
        product = create_product(plan_key, plan_config)
        if not product:
            continue
            
        # Create price
        price = create_price(product.id, plan_key, plan_config)
        if not price:
            continue
            
        # Store results
        results[plan_key] = {
            'product_id': product.id,
            'price_id': price.id,
            'name': plan_config['name']
        }
    
    print("\n" + "=" * 60)
    print("🎉 Setup Complete!")
    print()
    
    if results:
        print("📋 Environment Variables to Add:")
        print()
        for plan_key, data in results.items():
            env_var = f"STRIPE_PRICE_{plan_key.upper()}"
            print(f"{env_var}={data['price_id']}")
        
        print()
        print("📝 Add these to your .env file or environment")
        print()
        print("🔗 Next Steps:")
        print("1. Add the price IDs to your environment variables")
        print("2. Deploy the infrastructure with: ./scripts/deployment/deploy_subscriptions.sh")
        print("3. Set up webhook endpoint in Stripe dashboard")
        print("4. Test the subscription flow")
        
    else:
        print("❌ No products/prices were created successfully")
        print("Please check the errors above and try again")

if __name__ == "__main__":
    main()
