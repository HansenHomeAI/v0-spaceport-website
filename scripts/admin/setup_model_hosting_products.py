#!/usr/bin/env python3
"""
Stripe setup script for model training + hosting products.
Creates one product with a one-time training fee and a recurring hosting fee.
"""

import os
import sys
from typing import Dict, Any, Optional

import stripe


stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

PRODUCT_NAME = "3D AI Model Training & Hosting"
TRAINING_PRICE_CENTS = 60000
HOSTING_PRICE_CENTS = 2900


def _create_product() -> Optional[Dict[str, Any]]:
    try:
        return stripe.Product.create(
            name=PRODUCT_NAME,
            description="One-time AI model training plus monthly hosting",
            metadata={
                "product_type": "model_hosting",
            },
        )
    except Exception as exc:
        print(f"Error creating product: {exc}")
        return None


def _create_training_price(product_id: str) -> Optional[Dict[str, Any]]:
    try:
        return stripe.Price.create(
            product=product_id,
            unit_amount=TRAINING_PRICE_CENTS,
            currency="usd",
            metadata={
                "price_type": "model_training",
                "billing": "one_time",
            },
        )
    except Exception as exc:
        print(f"Error creating training price: {exc}")
        return None


def _create_hosting_price(product_id: str) -> Optional[Dict[str, Any]]:
    try:
        return stripe.Price.create(
            product=product_id,
            unit_amount=HOSTING_PRICE_CENTS,
            currency="usd",
            recurring={"interval": "month"},
            metadata={
                "price_type": "model_hosting",
                "billing": "recurring",
            },
        )
    except Exception as exc:
        print(f"Error creating hosting price: {exc}")
        return None


def main() -> int:
    if not stripe.api_key:
        print("STRIPE_SECRET_KEY is not set.")
        return 1

    try:
        stripe.Account.retrieve()
    except Exception as exc:
        print(f"Stripe connection failed: {exc}")
        return 1

    product = _create_product()
    if not product:
        return 1

    training_price = _create_training_price(product["id"])
    hosting_price = _create_hosting_price(product["id"])

    if not training_price or not hosting_price:
        return 1

    print("Stripe setup complete.")
    print()
    print("Add these price IDs to your environment secrets:")
    print(f"STRIPE_MODEL_TRAINING_PRICE_<ENV>={training_price['id']}")
    print(f"STRIPE_MODEL_HOSTING_PRICE_<ENV>={hosting_price['id']}")
    print()
    print("Example environments: STAGING, PROD.")
    print("Set STRIPE_SECRET_KEY_<ENV> as well if not already configured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
