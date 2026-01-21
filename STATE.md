reason: Missing Stripe secret key to generate new $599 price IDs.
last_step: Updated training price constant in scripts/admin/setup_model_hosting_products.py to 59900.
next_unblocked_step: Run scripts/admin/setup_model_hosting_products.py with a Stripe secret key to create new price IDs, then update STRIPE_MODEL_TRAINING_PRICE_* secrets and redeploy.
owner_action_needed: Provide new Stripe price IDs for $599 training (live + test) or run the script with STRIPE_SECRET_KEY and share the resulting IDs.
