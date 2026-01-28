#!/usr/bin/env python3
"""
Stripe setup script for model training + hosting products.
Creates separate products for training (one-time) and hosting (recurring).
"""

import os
import sys
from typing import Dict, Any, Optional

import stripe


stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

TRAINING_PRODUCT_NAME = "AI Model Training"
HOSTING_PRODUCT_NAME = "Web Hosting"
TRAINING_PRICE_CENTS = 59900
HOSTING_PRICE_CENTS = 2900


def _create_training_product() -> Optional[Dict[str, Any]]:
    try:
        return stripe.Product.create(
            name=TRAINING_PRODUCT_NAME,
            metadata={
                "product_type": "model_training",
            },
        )
    except Exception as exc:
        print(f"Error creating product: {exc}")
        return None


def _create_hosting_product() -> Optional[Dict[str, Any]]:
    try:
        return stripe.Product.create(
            name=HOSTING_PRODUCT_NAME,
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

    training_product = _create_training_product()
    hosting_product = _create_hosting_product()
    if not training_product or not hosting_product:
        return 1

    training_price = _create_training_price(training_product["id"])
    hosting_price = _create_hosting_price(hosting_product["id"])

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
