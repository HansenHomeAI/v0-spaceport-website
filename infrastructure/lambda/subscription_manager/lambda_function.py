import json
import os
import boto3
import stripe
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, Union
from decimal import Decimal
import logging
from botocore.exceptions import ClientError
from botocore.config import Config
from urllib.parse import urlparse

# Sentry for error tracking
try:
    import sentry_sdk
    from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration
    from sentry_sdk.integrations.boto3 import Boto3Integration
    
    # Initialize Sentry
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[
            AwsLambdaIntegration(),
            Boto3Integration(),
        ],
        traces_sample_rate=0.1,
        environment=os.environ.get('ENVIRONMENT', 'production'),
    )
except ImportError:
    # Sentry not available, continue without it
    pass

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Initialize AWS services
dynamodb = boto3.resource('dynamodb')
cognito_idp = boto3.client('cognito-idp')

_USERS_TABLE_KEY_CACHE: Dict[str, str] = {}


def _resolve_users_table() -> Tuple[Any, str]:
    """Return the DynamoDB table resource and its hash key attribute."""
    table = dynamodb.Table(USERS_TABLE)

    cached_key = _USERS_TABLE_KEY_CACHE.get(USERS_TABLE)
    if cached_key:
        return table, cached_key

    key_name = 'userSub'
    try:
        key_schema = getattr(table, 'key_schema', [])
        for entry in key_schema:
            if entry.get('KeyType') == 'HASH':
                key_name = entry.get('AttributeName', key_name)
                break
    except Exception as exc:  # pragma: no cover - defensive logging only
        logger.warning("Failed to inspect key schema for %s: %s", USERS_TABLE, exc)

    _USERS_TABLE_KEY_CACHE[USERS_TABLE] = key_name
    return table, key_name


def _build_user_key(primary_key: str, user_id: str) -> Dict[str, str]:
    return {primary_key: user_id}


def _enrich_user_identifiers(payload: Dict[str, Any], user_id: str, primary_key: str) -> None:
    payload.setdefault('userSub', user_id)
    payload.setdefault('userId', user_id)
    payload.setdefault('id', user_id)
    payload[primary_key] = user_id


def _coerce_decimal(value: Union[Dict[str, Any], list, Decimal, Any]) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    if isinstance(value, list):
        return [_coerce_decimal(v) for v in value]
    if isinstance(value, dict):
        return {k: _coerce_decimal(v) for k, v in value.items()}
    return value

# Table names - using existing users table
USERS_TABLE = os.environ.get('USERS_TABLE', 'Spaceport-Users')
PROJECTS_TABLE_NAME = os.environ.get('PROJECTS_TABLE_NAME', 'Spaceport-Projects')

# R2 configuration (S3-compatible)
R2_ENDPOINT = os.environ.get('R2_ENDPOINT')
R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', 'spaces-viewers')
R2_REGION = os.environ.get('R2_REGION', 'auto')

# Referral configuration - UPDATED FOR NEW STRUCTURE
REFERRAL_KICKBACK_PERCENTAGE = int(os.environ.get('REFERRAL_KICKBACK_PERCENTAGE', '10'))
EMPLOYEE_KICKBACK_PERCENTAGE = int(os.environ.get('EMPLOYEE_KICKBACK_PERCENTAGE', '30'))
COMPANY_KICKBACK_PERCENTAGE = int(os.environ.get('COMPANY_KICKBACK_PERCENTAGE', '70'))
REFERRAL_DURATION_MONTHS = int(os.environ.get('REFERRAL_DURATION_MONTHS', '6'))

# Employee user ID (you'll need to set this)
EMPLOYEE_USER_ID = os.environ.get('EMPLOYEE_USER_ID', '')


def _get_projects_table() -> Optional[Any]:
    if not PROJECTS_TABLE_NAME:
        return None
    return dynamodb.Table(PROJECTS_TABLE_NAME)


def _get_r2_client() -> Optional[Any]:
    if not (R2_ENDPOINT and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY):
        logger.warning("R2 configuration missing; restore operations disabled.")
        return None

    return boto3.client(
        's3',
        region_name=R2_REGION,
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4'),
    )


def _r2_object_exists(client: Any, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        code = exc.response.get('Error', {}).get('Code')
        if code in ('404', 'NoSuchKey', 'NotFound'):
            return False
        raise


def _resolve_viewer_slug(project: Dict[str, Any]) -> Optional[str]:
    for key in ('viewerSlug', 'viewer_slug', 'slug'):
        slug = project.get(key)
        if slug:
            return slug

    delivery = project.get('delivery') or {}
    for key in ('viewerSlug', 'viewer_slug'):
        slug = delivery.get(key)
        if slug:
            return slug

    model_link = delivery.get('modelLink') or project.get('modelLink')
    if model_link:
        parsed = urlparse(model_link)
        path = parsed.path or ''
        if '/spaces/' in path:
            slug = path.split('/spaces/', 1)[1].strip('/').split('/')[0]
            if slug:
                return slug
        parts = [part for part in path.split('/') if part]
        if parts:
            return parts[-1]

    return None


def _restore_revoked_model(project: Dict[str, Any]) -> None:
    if not R2_BUCKET_NAME:
        logger.warning("R2_BUCKET_NAME is missing; cannot restore model viewer.")
        return

    slug = _resolve_viewer_slug(project)
    if not slug:
        logger.warning("Unable to resolve viewer slug for project restore.")
        return

    client = _get_r2_client()
    if not client:
        return

    original_key = f"models/{slug}/original.html"
    index_key = f"models/{slug}/index.html"

    if not _r2_object_exists(client, R2_BUCKET_NAME, original_key):
        logger.warning("original.html missing for slug %s; skipping restore.", slug)
        return

    try:
        client.copy_object(
            Bucket=R2_BUCKET_NAME,
            CopySource={'Bucket': R2_BUCKET_NAME, 'Key': original_key},
            Key=index_key,
        )
        client.delete_object(Bucket=R2_BUCKET_NAME, Key=original_key)
        logger.info("Restored viewer for slug %s", slug)
    except ClientError as exc:
        logger.error("Failed to restore viewer for slug %s: %s", slug, exc)


def _handle_project_checkout_completed(session: Dict[str, Any]) -> None:
    metadata = session.get('metadata') or {}
    project_id = metadata.get('projectId')
    user_sub = metadata.get('userSub') or metadata.get('user_id')

    if not project_id or not user_sub:
        logger.warning("Checkout session missing project metadata.")
        return

    table = _get_projects_table()
    if not table:
        logger.warning("Projects table is unavailable; cannot update payment state.")
        return

    project = table.get_item(Key={'userSub': user_sub, 'projectId': project_id}).get('Item')
    if not project:
        logger.warning("Project not found for payment update: %s", project_id)
        return

    was_revoked = (project.get('status') or '').lower() == 'revoked'
    now_epoch = int(datetime.utcnow().timestamp())

    update_expression_parts = ['SET paymentStatus = :paid', 'updatedAt = :updatedAt']
    expr_attr_values = {
        ':paid': 'paid',
        ':updatedAt': now_epoch,
    }
    expr_attr_names = {}

    if was_revoked:
        update_expression_parts.append('#status = :status')
        expr_attr_names['#status'] = 'status'
        expr_attr_values[':status'] = 'delivered'

    update_kwargs = {
        'Key': {'userSub': user_sub, 'projectId': project_id},
        'UpdateExpression': ', '.join(update_expression_parts),
        'ExpressionAttributeValues': expr_attr_values,
    }
    if expr_attr_names:
        update_kwargs['ExpressionAttributeNames'] = expr_attr_names

    table.update_item(**update_kwargs)

    if was_revoked:
        _restore_revoked_model(project)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for subscription management
    """
    try:
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')

        # Normalize API Gateway resource prefix to match internal routing
        # API resources are defined under '/subscription/*', but internal
        # handlers expect paths without the '/subscription' prefix.
        if isinstance(path, str) and path.startswith('/subscription'):
            normalized = path[len('/subscription'):] or '/'
            logger.info(f"Normalizing path from {path} to {normalized}")
            path = normalized

        logger.info(f"Processing {http_method} request to {path}")
        
        if http_method == 'POST' and path == '/create-checkout-session':
            return create_checkout_session(event)
        elif http_method == 'POST' and path == '/webhook':
            return handle_webhook(event)
        elif http_method == 'GET' and path == '/subscription-status':
            return get_subscription_status(event)
        elif http_method == 'POST' and path == '/cancel-subscription':
            return cancel_subscription(event)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid endpoint'})
            }
            
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }

def create_checkout_session(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a Stripe checkout session for subscription - NO TRIAL PERIOD
    """
    try:
        body = json.loads(event.get('body', '{}'))
        plan_type = body.get('planType')
        user_id = body.get('userId')
        referral_code = body.get('referralCode')
        
        if not plan_type or not user_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing planType or userId'})
            }
        
        # Get price ID based on plan type
        price_id = get_price_id(plan_type)
        if not price_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid plan type'})
            }
        
        # Create checkout session - NO TRIAL PERIOD
        session_data = {
            'payment_method_types': ['card'],
            'line_items': [{
                'price': price_id,
                'quantity': 1,
            }],
            'mode': 'subscription',
            'success_url': f"{os.environ.get('FRONTEND_URL', 'https://spcprt.com')}/create?subscription=success",
            'cancel_url': f"{os.environ.get('FRONTEND_URL', 'https://spcprt.com')}/pricing?canceled=true",
            'metadata': {
                'user_id': user_id,
                'plan_type': plan_type,
                'referral_code': referral_code or ''
            },
            'subscription_data': {
                'metadata': {
                    'user_id': user_id,
                    'plan_type': plan_type,
                    'referral_code': referral_code or ''
                }
            }
        }
        
        # NO TRIAL PERIOD - removed trial_period_days
        
        checkout_session = stripe.checkout.Session.create(**session_data)
        
        # Store referral tracking if provided
        if referral_code:
            store_referral_tracking(user_id, referral_code, plan_type)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'sessionId': checkout_session.id,
                'url': checkout_session.url
            })
        }
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to create checkout session'})
        }

def handle_webhook(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle Stripe webhook events
    """
    try:
        # Get raw body, handling base64 if needed
        body = event.get('body', '')
        is_base64 = event.get('isBase64Encoded', False)
        if is_base64 and body:
            import base64
            body = base64.b64decode(body).decode('utf-8')
            logger.info(f"DEBUG: Decoded base64 body, length: {len(body)}")
        
        # Case-insensitive header lookup
        headers = {k.lower(): v for k, v in event.get('headers', {}).items()}
        sig_header = headers.get('stripe-signature', '')
        
        # Enhanced debug logging
        logger.info(f"DEBUG: isBase64Encoded: {is_base64}")
        logger.info(f"DEBUG: Headers (normalized): {list(headers.keys())}")
        logger.info(f"DEBUG: stripe-signature header: '{sig_header}'")
        logger.info(f"DEBUG: Raw body length: {len(body) if body else 0}")
        
        if not body or not sig_header:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing webhook signature or body'})
            }
        
        # Verify webhook signature
        webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        if not webhook_secret:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Webhook secret not configured'})
            }
        
        try:
            stripe_event = stripe.Webhook.construct_event(
                body, sig_header, webhook_secret
            )
        except ValueError as e:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid payload'})
            }
        except stripe.error.SignatureVerificationError as e:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid signature'})
            }
        
        # Handle the event
        if stripe_event['type'] == 'checkout.session.completed':
            handle_checkout_completed(stripe_event['data']['object'])
        elif stripe_event['type'] == 'customer.subscription.created':
            handle_subscription_created(stripe_event['data']['object'])
        elif stripe_event['type'] == 'customer.subscription.updated':
            handle_subscription_updated(stripe_event['data']['object'])
        elif stripe_event['type'] == 'customer.subscription.deleted':
            handle_subscription_deleted(stripe_event['data']['object'])
        elif stripe_event['type'] == 'invoice.payment_succeeded':
            handle_payment_succeeded(stripe_event['data']['object'])
        elif stripe_event['type'] == 'invoice.payment_failed':
            handle_payment_failed(stripe_event['data']['object'])
        
        return {
            'statusCode': 200,
            'body': json.dumps({'received': True})
        }
        
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Webhook handling failed'})
        }

def handle_checkout_completed(session: Dict[str, Any]) -> None:
    """
    Handle successful checkout completion
    """
    try:
        metadata = session.get('metadata') or {}
        if metadata.get('projectId'):
            _handle_project_checkout_completed(session)
            return

        user_id = metadata.get('user_id')
        plan_type = metadata.get('plan_type')
        referral_code = metadata.get('referral_code')
        
        if user_id and plan_type:
            # Update user subscription status
            update_user_subscription(user_id, session['subscription'], plan_type, 'active')
            
            # Process referral if applicable
            if referral_code:
                process_referral(user_id, referral_code, plan_type)
                
    except Exception as e:
        logger.error(f"Error handling checkout completed: {str(e)}")

def handle_subscription_created(subscription: Dict[str, Any]) -> None:
    """
    Handle new subscription creation
    """
    try:
        user_id = subscription['metadata'].get('user_id')
        plan_type = subscription['metadata'].get('plan_type')
        
        if user_id and plan_type:
            update_user_subscription(user_id, subscription['id'], plan_type, subscription['status'])
            
    except Exception as e:
        logger.error(f"Error handling subscription created: {str(e)}")

def handle_subscription_updated(subscription: Dict[str, Any]) -> None:
    """
    Handle subscription updates
    """
    try:
        user_id = subscription['metadata'].get('user_id')
        if user_id:
            update_user_subscription(user_id, subscription['id'], 
                                  subscription['metadata'].get('plan_type'), 
                                  subscription['status'])
            
    except Exception as e:
        logger.error(f"Error handling subscription updated: {str(e)}")

def handle_subscription_deleted(subscription: Dict[str, Any]) -> None:
    """
    Handle subscription cancellation/deletion
    """
    try:
        user_id = subscription['metadata'].get('user_id')
        if user_id:
            update_user_subscription(user_id, subscription['id'], 
                                  subscription['metadata'].get('plan_type'), 
                                  'canceled')
            
    except Exception as e:
        logger.error(f"Error handling subscription deleted: {str(e)}")

def handle_payment_succeeded(invoice: Dict[str, Any]) -> None:
    """
    Handle successful payment - process referral payouts
    """
    try:
        subscription_id = invoice.get('subscription')
        if subscription_id:
            # Process referral payouts with new structure
            process_referral_payouts_new_structure(subscription_id, invoice['amount_paid'])
            
    except Exception as e:
        logger.error(f"Error handling payment succeeded: {str(e)}")

def handle_payment_failed(invoice: Dict[str, Any]) -> None:
    """
    Handle failed payment
    """
    try:
        subscription_id = invoice.get('subscription')
        if subscription_id:
            # Update subscription status to past_due
            update_subscription_status(subscription_id, 'past_due')
            
    except Exception as e:
        logger.error(f"Error handling payment failed: {str(e)}")

def get_price_id(plan_type: str) -> Optional[str]:
    """
    Get Stripe price ID for plan type
    """
    price_mapping = {
        'single': os.environ.get('STRIPE_PRICE_SINGLE'),
        'starter': os.environ.get('STRIPE_PRICE_STARTER'),
        'growth': os.environ.get('STRIPE_PRICE_GROWTH')
    }
    return price_mapping.get(plan_type)

def update_user_subscription(user_sub: str, subscription_id: Optional[str], plan_type: Optional[str], status: Optional[str]) -> None:
    """Persist subscription state in DynamoDB with idempotent model limits."""
    try:
        table, primary_key = _resolve_users_table()

        # Load or bootstrap the user's profile so we always have a baseline to build from.
        try:
            response = table.get_item(Key=_build_user_key(primary_key, user_sub))
        except ClientError as err:
            logger.error("Failed to load user %s from %s: %s", user_sub, USERS_TABLE, err)
            return

        current_data = response.get('Item')
        if not current_data:
            current_data = create_default_user_profile(user_sub, table=table, primary_key=primary_key)
        else:
            # Ensure we don't accidentally mutate the cached response.
            current_data = dict(current_data)
            _enrich_user_identifiers(current_data, user_sub, primary_key)

        now_iso = datetime.utcnow().isoformat()

        normalized_plan_type = (plan_type or current_data.get('planType') or DEFAULT_PLAN_TYPE).lower()
        normalized_status = (status or current_data.get('status') or 'active').lower()

        base_plan_type = current_data.get('basePlanType', DEFAULT_PLAN_TYPE)
        base_features = get_plan_features_new_structure(base_plan_type)
        base_max_models = base_features.get('maxModels', SUBSCRIPTION_TIERS[DEFAULT_PLAN_TYPE]['maxModels'])
        base_support = base_features.get('support', SUBSCRIPTION_TIERS[DEFAULT_PLAN_TYPE]['support'])
        base_trial_days = base_features.get('trialDays', SUBSCRIPTION_TIERS[DEFAULT_PLAN_TYPE]['trialDays'])

        selected_plan_features = get_plan_features_new_structure(normalized_plan_type)
        addon_models = selected_plan_features.get('maxModels', 0)
        is_active = normalized_status in ACTIVE_SUBSCRIPTION_STATUSES

        # Determine the effective model limit and support level the account should honor.
        if normalized_plan_type == 'enterprise' and is_active:
            effective_max_models = -1
            effective_support = selected_plan_features.get('support', base_support)
            effective_trial_days = selected_plan_features.get('trialDays', base_trial_days)
        else:
            if addon_models == -1:
                addon_models = 0  # Only enterprise should mark unlimited; other plans cannot.

            if is_active:
                effective_max_models = base_max_models + max(addon_models, 0)
                effective_support = selected_plan_features.get('support', base_support)
                effective_trial_days = selected_plan_features.get('trialDays', base_trial_days)
            else:
                effective_max_models = base_max_models
                effective_support = base_support
                effective_trial_days = base_trial_days

            if effective_max_models != -1 and effective_max_models < base_max_models:
                effective_max_models = base_max_models

        # Compose plan features for downstream consumers. The maxModels value reflects
        # the total capacity the user should see, not just the add-on delta.
        aggregated_plan_features: Dict[str, Any] = {
            'maxModels': effective_max_models,
            'support': effective_support,
            'trialDays': effective_trial_days,
            'displayName': selected_plan_features.get('displayName'),
            'price': selected_plan_features.get('price'),
            'baseMaxModels': base_max_models
        }
        if addon_models not in (0, -1):
            aggregated_plan_features['addonMaxModels'] = addon_models

        previous_max = current_data.get('maxModels', base_max_models)
        subscription_history = current_data.get('subscriptionHistory', [])
        subscription_history.append({
            'planType': normalized_plan_type,
            'status': normalized_status,
            'previousMax': previous_max,
            'newMax': effective_max_models,
            'timestamp': now_iso
        })
        subscription_history = subscription_history[-25:]

        subscription_payload: Dict[str, Any] = {
            'userSub': user_sub,
            'userId': user_sub,  # Legacy compatibility field
            'subscriptionId': subscription_id or current_data.get('subscriptionId'),
            'SubType': normalized_plan_type,
            'planType': normalized_plan_type,
            'status': normalized_status,
            'updatedAt': now_iso,
            'planFeatures': aggregated_plan_features,
            'maxModels': effective_max_models,
            'support': effective_support,
            'subscriptionHistory': subscription_history,
            'basePlanType': base_plan_type,
            'baseMaxModels': base_max_models,
            'createdAt': current_data.get('createdAt', now_iso)
        }

        # Preserve optional referral tracking fields if they already exist.
        for key in ('referralCode', 'referredBy', 'referralEarnings'):
            if key in current_data:
                subscription_payload[key] = current_data[key]

        _enrich_user_identifiers(subscription_payload, user_sub, primary_key)
        table.put_item(Item=subscription_payload)

        update_cognito_subscription_attributes(user_sub, normalized_plan_type, normalized_status)

    except Exception as e:
        logger.error(f"Error updating user subscription: {str(e)}")

# SUBSCRIPTION TIERS CONFIGURATION - ADDITIVE MODEL LIMITS
SUBSCRIPTION_TIERS = {
    'beta': {
        'maxModels': 5,  # Beta users start with 5 models
        'support': 'email',
        'price': 0,
        'displayName': 'Beta Plan',
        'trialDays': 0
    },
    'single': {
        'maxModels': 1,  # Adds 1 model to existing limit
        'support': 'email',
        'price': 29,
        'displayName': 'Single Model',
        'trialDays': 0
    },
    'starter': {
        'maxModels': 5,  # Adds 5 models to existing limit
        'support': 'priority',
        'price': 99,
        'displayName': 'Starter',
        'trialDays': 0
    },
    'growth': {
        'maxModels': 20,  # Adds 20 models to existing limit
        'support': 'dedicated',
        'price': 299,
        'displayName': 'Growth',
        'trialDays': 0
    },
    'enterprise': {
        'maxModels': -1,  # Unlimited (sets to unlimited regardless of current)
        'support': 'dedicated',
        'price': 0,  # Custom pricing / handled separately
        'displayName': 'Enterprise',
        'trialDays': 0
    }
}

ACTIVE_SUBSCRIPTION_STATUSES = {'active', 'trialing', 'past_due'}
DEFAULT_PLAN_TYPE = 'beta'

def get_plan_features_new_structure(plan_type: str) -> Dict[str, Any]:
    """
    Get features for a specific plan - UPDATED WITH BETA TIER
    """
    selected_plan = SUBSCRIPTION_TIERS.get(plan_type, SUBSCRIPTION_TIERS[DEFAULT_PLAN_TYPE])
    return deepcopy(selected_plan)

def update_cognito_subscription_attributes(user_id: str, plan_type: str, status: str) -> None:
    """
    Update Cognito user attributes with subscription info
    """
    try:
        cognito_idp.admin_update_user_attributes(
            UserPoolId=os.environ.get('COGNITO_USER_POOL_ID'),
            Username=user_id,
            UserAttributes=[
                {
                    'Name': 'custom:subscription_plan',
                    'Value': plan_type
                },
                {
                    'Name': 'custom:subscription_status',
                    'Value': status
                },
                {
                    'Name': 'custom:subscription_updated',
                    'Value': datetime.utcnow().isoformat()
                }
            ]
        )
    except Exception as e:
        logger.error(f"Error updating Cognito attributes: {str(e)}")

def store_referral_tracking(user_id: str, referral_code: str, plan_type: str) -> None:
    """
    Store referral tracking information
    """
    try:
        table, primary_key = _resolve_users_table()
        
        # Store referral data in user record
        table.update_item(
            Key=_build_user_key(primary_key, user_id),
            UpdateExpression='SET referralCode = :code, planType = :plan, referralStatus = :status, createdAt = if_not_exists(createdAt, :created), userId = :user_id, userSub = if_not_exists(userSub, :user_id), id = if_not_exists(id, :user_id)',
            ExpressionAttributeValues={
                ':code': referral_code,
                ':plan': plan_type,
                ':status': 'pending',
                ':created': datetime.utcnow().isoformat(),
                ':user_id': user_id
            }
        )
        
    except Exception as e:
        logger.error(f"Error storing referral tracking: {str(e)}")

def process_referral(user_id: str, referral_code: str, plan_type: str) -> None:
    """
    Process referral and set up tracking
    """
    try:
        # Find user with this referral code
        referred_by_user = find_user_by_handle(referral_code)
        if not referred_by_user:
            logger.warning(f"Referral code {referral_code} not found")
            return
        
        # Update referral tracking in user record
        table, primary_key = _resolve_users_table()
        table.update_item(
            Key=_build_user_key(primary_key, user_id),
            UpdateExpression='SET referredBy = :referred_by, referralStatus = :status, userId = :user_id, userSub = if_not_exists(userSub, :user_id), id = if_not_exists(id, :user_id)',
            ExpressionAttributeValues={
                ':referred_by': referred_by_user,
                ':status': 'active',
                ':user_id': user_id
            }
        )
        
        # Set up referral payout tracking with NEW STRUCTURE
        setup_referral_payouts_new_structure(referred_by_user, user_id, plan_type)
        
    except Exception as e:
        logger.error(f"Error processing referral: {str(e)}")

def find_user_by_handle(handle: str) -> Optional[str]:
    """
    Find user ID by handle (preferred_username)
    """
    try:
        # This would need to be implemented based on your user storage
        # For now, we'll assume users are stored in DynamoDB with handles
        table, _ = _resolve_users_table()
        response = table.scan(
            FilterExpression='preferred_username = :handle',
            ExpressionAttributeValues={':handle': handle}
        )
        
        items = response.get('Items', [])
        if items:
            item = items[0]
            return item.get('userSub') or item.get('userId') or item.get('id')
        
        return None
        
    except Exception as e:
        logger.error(f"Error finding user by handle: {str(e)}")
        return None

def setup_referral_payouts_new_structure(referred_by_user: str, new_user: str, plan_type: str) -> None:
    """
    Set up referral payout tracking - NEW STRUCTURE
    """
    try:
        # Calculate payout amounts based on new structure
        plan_prices = {
            'single': 29,
            'starter': 99,
            'growth': 299
        }
        
        monthly_amount = plan_prices.get(plan_type, 0)
        total_referee_kickback = (monthly_amount * REFERRAL_KICKBACK_PERCENTAGE) / 100
        
        # NEW STRUCTURE: 30% to employee, 70% to company
        employee_kickback = (total_referee_kickback * EMPLOYEE_KICKBACK_PERCENTAGE) / 100
        company_kickback = (total_referee_kickback * COMPANY_KICKBACK_PERCENTAGE) / 100
        
        # Store payout tracking in user record
        table, primary_key = _resolve_users_table()
        
        # Update user's referral earnings
        table.update_item(
            Key=_build_user_key(primary_key, referred_by_user),
            UpdateExpression='SET referralEarnings = :earnings, lastReferralUpdate = :updated, userId = :user_id, userSub = if_not_exists(userSub, :user_id), id = if_not_exists(id, :user_id)',
            ExpressionAttributeValues={
                ':earnings': {
                    'totalUsd': total_referee_kickback,
                    'employeeUsdAccrued': employee_kickback,
                    'companyUsdAccrued': company_kickback,
                    'monthsRemaining': REFERRAL_DURATION_MONTHS,
                    'lastUpdated': datetime.utcnow().isoformat()
                },
                ':updated': datetime.utcnow().isoformat(),
                ':user_id': referred_by_user
            }
        )
        
        # Note: Employee and company payouts are tracked in the user's referralEarnings
        # Manual payouts will be handled based on these accruals
            
    except Exception as e:
        logger.error(f"Error setting up referral payouts: {str(e)}")

def process_referral_payouts_new_structure(subscription_id: str, amount_paid: int) -> None:
    """
    Process referral payouts for successful payment - NEW STRUCTURE
    """
    try:
        # Find referral payouts for this subscription
        table, primary_key = _resolve_users_table()
        response = table.scan(
            FilterExpression='referredUser = :subscription_id AND #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':subscription_id': subscription_id, ':status': 'active'}
        )
        
        items = response.get('Items', [])
        for item in items:
            months_remaining = item.get('monthsRemaining', 0)
            if months_remaining <= 0:
                continue

            user_sub = item.get('userId') or item.get('userSub') or item.get(primary_key)
            if not user_sub:
                logger.warning('Referral payout item missing user identifier, skipping: %s', item)
                continue

            monthly_kickback = item.get('monthlyKickback', 0)
            total_kickback = item.get('totalKickback', 0)
            new_total = total_kickback + monthly_kickback
            new_months_remaining = max(months_remaining - 1, 0)

            try:
                table.update_item(
                    Key=_build_user_key(primary_key, user_sub),
                    UpdateExpression='SET referralEarnings.totalUsd = :total, referralEarnings.monthsRemaining = :months, referralEarnings.lastUpdated = :updated',
                    ExpressionAttributeValues={
                        ':total': new_total,
                        ':months': new_months_remaining,
                        ':updated': datetime.utcnow().isoformat()
                    }
                )
                logger.info(f"Processed referral payout: {monthly_kickback} for user {user_sub}")
            except Exception as update_error:
                logger.error(
                    "Error updating referral payout tracking for user %s: %s",
                    user_sub,
                    update_error
                )

    except Exception as e:
        logger.error(f"Error processing referral payouts: {str(e)}")

def get_subscription_status(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get user subscription status - UPDATED TO RETURN BETA BY DEFAULT
    """
    try:
        # Extract userSub from JWT token
        user_sub = extract_user_sub_from_jwt(event)
        if not user_sub:
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized'})
            }
        
        # Get subscription from DynamoDB
        table, primary_key = _resolve_users_table()
        try:
            response = table.get_item(Key=_build_user_key(primary_key, user_sub))
        except ClientError as err:
            logger.error("Failed to fetch subscription status for %s: %s", user_sub, err)
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to get subscription status'})
            }

        if 'Item' in response:
            user_data = dict(response['Item'])
        else:
            user_data = create_default_user_profile(user_sub, table=table, primary_key=primary_key)

        plan_type = user_data.get('planType', DEFAULT_PLAN_TYPE)
        plan_features = user_data.get('planFeatures', get_plan_features_new_structure(plan_type))

        # Build subscription response from user data
        subscription = {
            'status': user_data.get('status', 'active'),
            'planType': plan_type,
            'SubType': plan_type,
            'planFeatures': plan_features,
            'subscriptionId': user_data.get('subscriptionId'),
            'maxModels': user_data.get('maxModels', plan_features.get('maxModels')),
            'support': user_data.get('support', plan_features.get('support', 'email')),
            'subscriptionHistory': user_data.get('subscriptionHistory', []),
            'referredBy': user_data.get('referredBy'),
            'referralCode': user_data.get('referralCode'),
            'referralEarnings': user_data.get('referralEarnings', 0)
        }

        subscription = _coerce_decimal(subscription)
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'subscription': subscription
            })
        }
            
    except Exception as e:
        logger.error(f"Error getting subscription status: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to get subscription status'})
        }

def cancel_subscription(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cancel user subscription - UPDATED TO USE userSub
    """
    try:
        user_sub = extract_user_sub_from_jwt(event)
        if not user_sub:
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized'})
            }
        
        # Get subscription ID
        table, primary_key = _resolve_users_table()
        try:
            response = table.get_item(Key=_build_user_key(primary_key, user_sub))
        except ClientError as err:
            logger.error("Failed to load subscription for cancellation for %s: %s", user_sub, err)
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to cancel subscription'})
            }

        if 'Item' not in response:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'No subscription found'})
            }

        subscription_id = response['Item'].get('subscriptionId')
        if not subscription_id:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'No subscription ID found'})
            }
        
        # Cancel in Stripe
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        
        # Update local status
        update_user_subscription(
            user_sub,
            subscription_id,
            response['Item'].get('planType', DEFAULT_PLAN_TYPE),
            'canceled'
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Subscription canceled successfully'})
        }
        
    except Exception as e:
        logger.error(f"Error canceling subscription: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to cancel subscription'})
        }

def extract_user_sub_from_jwt(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract userSub (Cognito sub) from JWT token - UPDATED
    """
    try:
        # Get the requestContext from API Gateway
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        
        # Extract 'sub' from Cognito JWT claims
        user_sub = authorizer.get('claims', {}).get('sub')
        
        if user_sub:
            return user_sub
            
        # Fallback: try to extract from headers (for testing)
        auth_header = event.get('headers', {}).get('Authorization', '')
        if auth_header.startswith('Bearer '):
            # In production, we'd decode and verify the JWT
            # For now, check if userSub is in headers for testing
            return event.get('headers', {}).get('X-User-Sub')
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting userSub from JWT: {str(e)}")
        return None

def create_default_user_profile(user_sub: str, table: Any = None, primary_key: Optional[str] = None) -> Dict[str, Any]:
    """Create a baseline beta subscription profile for new users."""
    plan_features = get_plan_features_new_structure(DEFAULT_PLAN_TYPE)
    plan_features.setdefault('baseMaxModels', plan_features.get('maxModels'))
    plan_features.setdefault('addonMaxModels', 0)
    now_iso = datetime.utcnow().isoformat()

    user_profile: Dict[str, Any] = {
        'userSub': user_sub,
        'userId': user_sub,
        'SubType': DEFAULT_PLAN_TYPE,
        'planType': DEFAULT_PLAN_TYPE,
        'status': 'active',
        'maxModels': plan_features.get('maxModels'),
        'support': plan_features.get('support', 'email'),
        'planFeatures': plan_features,
        'subscriptionId': None,
        'subscriptionHistory': [{
            'planType': DEFAULT_PLAN_TYPE,
            'status': 'active',
            'previousMax': 0,
            'newMax': plan_features.get('maxModels'),
            'timestamp': now_iso
        }],
        'createdAt': now_iso,
        'updatedAt': now_iso,
        'basePlanType': DEFAULT_PLAN_TYPE,
        'baseMaxModels': plan_features.get('maxModels')
    }

    try:
        if table is None or primary_key is None:
            table, primary_key = _resolve_users_table()

        _enrich_user_identifiers(user_profile, user_sub, primary_key)
        table.put_item(Item=user_profile)
        logger.info(f"Created default beta profile for user: {user_sub}")
    except Exception as e:
        logger.error(f"Error creating default user profile: {str(e)}")

    return user_profile

# Keep legacy function for backward compatibility
def extract_user_id_from_jwt(event: Dict[str, Any]) -> Optional[str]:
    """
    Legacy function - redirects to extract_user_sub_from_jwt
    """
    return extract_user_sub_from_jwt(event)

def update_subscription_status(subscription_id: str, status: str) -> None:
    """
    Update subscription status in DynamoDB
    """
    try:
        table = dynamodb.Table(USERS_TABLE)
        
        # Find subscription by subscription ID
        response = table.scan(
            FilterExpression='subscriptionId = :subscription_id',
            ExpressionAttributeValues={':subscription_id': subscription_id}
        )
        
        items = response.get('Items', [])
        if items:
            user_record = items[0]
            user_sub = user_record.get('userSub') or user_record.get('userId')
            if user_sub:
                update_user_subscription(
                    user_sub,
                    subscription_id,
                    user_record.get('planType', DEFAULT_PLAN_TYPE),
                    status
                )
            
    except Exception as e:
        logger.error(f"Error updating subscription status: {str(e)}")
