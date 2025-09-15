import json
import os
import boto3
import stripe
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Initialize AWS services
dynamodb = boto3.resource('dynamodb')
cognito_idp = boto3.client('cognito-idp')

# Table names - using existing users table
USERS_TABLE = os.environ.get('USERS_TABLE', 'Spaceport-Users')

# Referral configuration - UPDATED FOR NEW STRUCTURE
REFERRAL_KICKBACK_PERCENTAGE = int(os.environ.get('REFERRAL_KICKBACK_PERCENTAGE', '10'))
EMPLOYEE_KICKBACK_PERCENTAGE = int(os.environ.get('EMPLOYEE_KICKBACK_PERCENTAGE', '30'))
COMPANY_KICKBACK_PERCENTAGE = int(os.environ.get('COMPANY_KICKBACK_PERCENTAGE', '70'))
REFERRAL_DURATION_MONTHS = int(os.environ.get('REFERRAL_DURATION_MONTHS', '6'))

# Employee user ID (you'll need to set this)
EMPLOYEE_USER_ID = os.environ.get('EMPLOYEE_USER_ID', '')

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
        body = event.get('body', '')
        sig_header = event.get('headers', {}).get('stripe-signature', '')
        
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
        user_id = session['metadata'].get('user_id')
        plan_type = session['metadata'].get('plan_type')
        referral_code = session['metadata'].get('referral_code')
        
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

def update_user_subscription(user_sub: str, subscription_id: str, plan_type: str, status: str) -> None:
    """
    Update user subscription in DynamoDB - UPDATED TO USE userSub
    """
    try:
        table = dynamodb.Table(USERS_TABLE)
        
        # Get current user data using id (table partition key)
        response = table.get_item(Key={'id': user_sub})
        current_data = response.get('Item', {})
        
        # Get plan features from centralized config
        plan_features = get_plan_features_new_structure(plan_type)
        
        # Update subscription data
        subscription_data = {
            'id': user_sub,
            'subscriptionId': subscription_id,
            'SubType': plan_type,  # Main field for subscription tier
            'planType': plan_type,  # Keep for backward compatibility
            'status': status,
            'updatedAt': datetime.utcnow().isoformat(),
            'planFeatures': plan_features,
            'maxModels': plan_features.get('maxModels', 5),
            'support': plan_features.get('support', 'email')
        }
        
        # Preserve referral data if exists
        if 'referralCode' in current_data:
            subscription_data['referralCode'] = current_data['referralCode']
        if 'referredBy' in current_data:
            subscription_data['referredBy'] = current_data['referredBy']
        if 'referralEarnings' in current_data:
            subscription_data['referralEarnings'] = current_data['referralEarnings']
        
        # Add creation date if new subscription
        if 'createdAt' not in current_data:
            subscription_data['createdAt'] = datetime.utcnow().isoformat()
        
        table.put_item(Item=subscription_data)
        
        # Update Cognito user attributes
        update_cognito_subscription_attributes(user_sub, plan_type, status)
        
    except Exception as e:
        logger.error(f"Error updating user subscription: {str(e)}")

# SUBSCRIPTION TIERS CONFIGURATION
SUBSCRIPTION_TIERS = {
    'beta': {
        'maxModels': 5,
        'support': 'email',
        'price': 0,
        'displayName': 'Beta Plan'
    },
    'single': {
        'maxModels': 1,
        'support': 'email',
        'price': 29,
        'displayName': 'Single Model'
    },
    'starter': {
        'maxModels': 5,
        'support': 'priority',
        'price': 99,
        'displayName': 'Starter'
    },
    'growth': {
        'maxModels': 20,
        'support': 'dedicated',
        'price': 299,
        'displayName': 'Growth'
    },
    'enterprise': {
        'maxModels': -1,  # Unlimited
        'support': 'dedicated',
        'price': 0,  # Custom pricing
        'displayName': 'Enterprise'
    }
}

def get_plan_features_new_structure(plan_type: str) -> Dict[str, Any]:
    """
    Get features for a specific plan - UPDATED WITH BETA TIER
    """
    return SUBSCRIPTION_TIERS.get(plan_type, SUBSCRIPTION_TIERS['beta'])

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
        table = dynamodb.Table(USERS_TABLE)
        
        # Store referral data in user record
        table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET referralCode = :code, planType = :plan, referralStatus = :status, createdAt = :created',
            ExpressionAttributeValues={
                ':code': referral_code,
                ':plan': plan_type,
                ':status': 'pending',
                ':created': datetime.utcnow().isoformat()
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
        table = dynamodb.Table(USERS_TABLE)
        table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET referredBy = :referred_by, referralStatus = :status',
            ExpressionAttributeValues={
                ':referred_by': referred_by_user,
                ':status': 'active'
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
        table = dynamodb.Table(USERS_TABLE)
        response = table.scan(
            FilterExpression='preferred_username = :handle',
            ExpressionAttributeValues={':handle': handle}
        )
        
        items = response.get('Items', [])
        if items:
            return items[0].get('userId')
        
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
        table = dynamodb.Table(USERS_TABLE)
        
        # Update user's referral earnings
        table.update_item(
            Key={'userId': referred_by_user},
            UpdateExpression='SET referralEarnings = :earnings, lastReferralUpdate = :updated',
            ExpressionAttributeValues={
                ':earnings': {
                    'totalUsd': total_referee_kickback,
                    'employeeUsdAccrued': employee_kickback,
                    'companyUsdAccrued': company_kickback,
                    'monthsRemaining': REFERRAL_DURATION_MONTHS,
                    'lastUpdated': datetime.utcnow().isoformat()
                },
                ':updated': datetime.utcnow().isoformat()
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
        table = dynamodb.Table(USERS_TABLE)
        response = table.scan(
            FilterExpression='referredUser = :subscription_id AND #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':subscription_id': subscription_id, ':status': 'active'}
        )
        
        items = response.get('Items', [])
        for item in items:
            if item.get('monthsRemaining', 0) > 0:
                # Process payout
                monthly_kickback = item.get('monthlyKickback', 0)
                total_kickback = item.get('totalKickback', 0)
                months_remaining = item.get('monthsRemaining', 0)
                
                # Update payout tracking
                table.update_item(
                    Key={'userId': item['userId'], 'referralPayoutId': item['referralPayoutId']},
                    UpdateExpression='SET totalKickback = :total, monthsRemaining = :months',
                    ExpressionAttributeValues={
                        ':total': total_kickback + monthly_kickback,
                        ':months': months_remaining - 1
                    }
                )
                
                # If months expired, mark as completed
                if months_remaining - 1 <= 0:
                    table.update_item(
                        Key={'userId': item['userId'], 'referralPayoutId': item['referralPayoutId']},
                        UpdateExpression='SET #status = :status',
                        ExpressionAttributeNames={'#status': 'status'},
                        ExpressionAttributeValues={':status': 'completed'}
                    )
                
                # TODO: Implement actual payout to user/employee/company
                # This will require Stripe Connect for automated payouts
                logger.info(f"Processed referral payout: {monthly_kickback} for user {item['userId']}")
                
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
        table = dynamodb.Table(USERS_TABLE)
        response = table.get_item(Key={'id': user_sub})
        
        if 'Item' in response:
            user_data = response['Item']
            sub_type = user_data.get('SubType', 'beta')
            
            # Build subscription response from user data
            subscription = {
                'status': user_data.get('status', 'active'),
                'planType': sub_type,
                'SubType': sub_type,
                'planFeatures': get_plan_features_new_structure(sub_type),
                'subscriptionId': user_data.get('subscriptionId'),
                'referredBy': user_data.get('referredBy'),
                'referralEarnings': user_data.get('referralEarnings', 0)
            }
        else:
            # Create default beta user profile
            create_default_user_profile(user_sub)
            
            # Return default beta subscription
            subscription = {
                'status': 'active',
                'planType': 'beta',
                'SubType': 'beta',
                'planFeatures': get_plan_features_new_structure('beta'),
                'subscriptionId': None,
                'referredBy': None,
                'referralEarnings': 0
            }
        
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
        table = dynamodb.Table(USERS_TABLE)
        response = table.get_item(Key={'id': user_sub})
        
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
        update_user_subscription(user_sub, subscription_id, 
                              response['Item'].get('planType'), 'canceled')
        
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

def create_default_user_profile(user_sub: str) -> None:
    """
    Create default user profile with beta subscription
    """
    try:
        table = dynamodb.Table(USERS_TABLE)
        
        # Create default user profile
        user_profile = {
            'id': user_sub,
            'SubType': 'beta',  # Default to beta plan
            'planType': 'beta',
            'status': 'active',
            'maxModels': 5,
            'support': 'email',
            'planFeatures': get_plan_features_new_structure('beta'),
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat()
        }
        
        table.put_item(Item=user_profile)
        logger.info(f"Created default beta profile for user: {user_sub}")
        
    except Exception as e:
        logger.error(f"Error creating default user profile: {str(e)}")

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
            user_id = items[0]['userId']
            table.update_item(
                Key={'userId': user_id},
                UpdateExpression='SET subscription.status = :status, subscription.updatedAt = :updated_at',
                ExpressionAttributeValues={
                    ':status': status,
                    ':updated_at': datetime.utcnow().isoformat()
                }
            )
            
    except Exception as e:
        logger.error(f"Error updating subscription status: {str(e)}")
