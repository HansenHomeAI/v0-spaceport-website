#!/bin/bash

# Spaceport Subscription System Deployment Script
# This script deploys the subscription infrastructure and updates the frontend

set -e

echo "🚀 Starting Spaceport Subscription System Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required environment variables are set
check_env_vars() {
    print_status "Checking environment variables..."
    
    required_vars=(
        "STRIPE_SECRET_KEY"
        "STRIPE_PUBLISHABLE_KEY"
        "STRIPE_WEBHOOK_SECRET"
        "STRIPE_PRICE_SINGLE"
        "STRIPE_PRICE_STARTER"
        "STRIPE_PRICE_GROWTH"
        "EMPLOYEE_USER_ID"
        "REFERRAL_KICKBACK_PERCENTAGE"
        "EMPLOYEE_KICKBACK_PERCENTAGE"
        "COMPANY_KICKBACK_PERCENTAGE"
        "REFERRAL_DURATION_MONTHS"
    )
    
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        print_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        echo "Please set these variables in your environment or .env file"
        echo ""
        echo "Key changes from previous version:"
        echo "  - EMPLOYEE_USER_ID (instead of COFOUNDER_USER_ID)"
        echo "  - EMPLOYEE_KICKBACK_PERCENTAGE (30% of referee amount)"
        echo "  - COMPANY_KICKBACK_PERCENTAGE (70% of referee amount)"
        echo "  - All plans have NO TRIAL PERIOD"
        exit 1
    fi
    
    print_success "All required environment variables are set"
}

# Deploy CDK infrastructure
deploy_cdk() {
    print_status "Deploying CDK infrastructure..."
    
    cd infrastructure/spaceport_cdk
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_status "Installing CDK dependencies..."
        npm install
    fi
    
    # Deploy subscription stack
    print_status "Deploying subscription stack..."
    npx cdk deploy SpaceportSubscriptionStack --require-approval never
    
    # Get stack outputs
    SUBSCRIPTION_API_URL=$(npx cdk output SpaceportSubscriptionStack:SubscriptionApiUrl --output text)
    SUBSCRIPTIONS_TABLE=$(npx cdk output SpaceportSubscriptionStack:SubscriptionsTableName --output text)
    
    print_success "CDK deployment completed"
    print_status "Subscription API URL: $SUBSCRIPTION_API_URL"
    print_status "Subscriptions Table: $SUBSCRIPTIONS_TABLE"
    
    cd ../..
}

# Update frontend environment
update_frontend_env() {
    print_status "Updating frontend environment..."
    
    # Create .env.local file for frontend
    cat > web/.env.local << EOF
# Stripe Configuration
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=$STRIPE_PUBLISHABLE_KEY

# Subscription API
NEXT_PUBLIC_SUBSCRIPTION_API_URL=$SUBSCRIPTION_API_URL

# Other environment variables
NEXT_PUBLIC_REFERRAL_KICKBACK_PERCENTAGE=${REFERRAL_KICKBACK_PERCENTAGE:-10}
NEXT_PUBLIC_COFOUNDER_KICKBACK_PERCENTAGE=${COFOUNDER_KICKBACK_PERCENTAGE:-30}
NEXT_PUBLIC_REFERRAL_DURATION_MONTHS=${REFERRAL_DURATION_MONTHS:-6}
EOF
    
    print_success "Frontend environment updated"
}

# Build and deploy frontend
deploy_frontend() {
    print_status "Building frontend..."
    
    cd web
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_status "Installing frontend dependencies..."
        npm install
    fi
    
    # Build the application
    print_status "Building Next.js application..."
    npm run build
    
    print_success "Frontend build completed"
    
    cd ..
}

# Test subscription endpoints
test_endpoints() {
    print_status "Testing subscription endpoints..."
    
    if [ -z "$SUBSCRIPTION_API_URL" ]; then
        print_warning "Skipping endpoint tests - SUBSCRIPTION_API_URL not set"
        return
    fi
    
    # Test webhook endpoint (should return 400 for missing signature)
    print_status "Testing webhook endpoint..."
    curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$SUBSCRIPTION_API_URL/webhook" \
        -H "Content-Type: application/json" \
        -d '{"test": "data"}' || true
    
    print_success "Endpoint tests completed"
}

# Setup Stripe webhook
setup_stripe_webhook() {
    print_status "Setting up Stripe webhook..."
    
    if [ -z "$STRIPE_SECRET_KEY" ] || [ -z "$SUBSCRIPTION_API_URL" ]; then
        print_warning "Skipping Stripe webhook setup - missing credentials or API URL"
        return
    fi
    
    # Create webhook endpoint in Stripe
    print_status "Creating Stripe webhook endpoint..."
    
    # This would typically be done through the Stripe dashboard or CLI
    # For now, we'll provide instructions
    print_warning "Please manually create a webhook endpoint in your Stripe dashboard:"
    echo "  URL: $SUBSCRIPTION_API_URL/webhook"
    echo "  Events to send:"
    echo "    - checkout.session.completed"
    echo "    - customer.subscription.created"
    echo "    - customer.subscription.updated"
    echo "    - customer.subscription.deleted"
    echo "    - invoice.payment_succeeded"
    echo "    - invoice.payment_failed"
    echo ""
    echo "  After creating, update your environment with the webhook secret"
}

# Main deployment flow
main() {
    print_status "Starting deployment at $(date)"
    
    # Check environment
    check_env_vars
    
    # Deploy infrastructure
    deploy_cdk
    
    # Update frontend environment
    update_frontend_env
    
    # Deploy frontend
    deploy_frontend
    
    # Test endpoints
    test_endpoints
    
    # Setup Stripe webhook
    setup_stripe_webhook
    
    print_success "🎉 Subscription system deployment completed!"
    print_status ""
    print_status "Next steps:"
    print_status "1. Create Stripe products and prices in your dashboard"
    print_status "2. Set up webhook endpoint in Stripe dashboard"
    print_status "3. Update environment variables with webhook secret"
    print_status "4. Test subscription flow with test cards"
    print_status "5. Deploy frontend to your hosting platform"
    print_status ""
    print_status "For testing, use Stripe test cards:"
    print_status "  - Success: 4242 4242 4242 4242"
    print_status "  - Decline: 4000 0000 0000 0002"
    print_status ""
}

# Run main function
main "$@"
