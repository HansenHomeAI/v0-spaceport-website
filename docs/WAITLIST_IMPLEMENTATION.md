# Waitlist Implementation

## Overview

The Spaceport AI waitlist system is a production-ready solution that stores user submissions in DynamoDB and sends email notifications to administrators.

## Architecture

### Components

1. **DynamoDB Table**: `Spaceport-Waitlist`
   - Partition key: `email` (String)
   - Billing mode: Pay per request
   - Point-in-time recovery enabled
   - Retention policy: Retain on deletion

2. **Lambda Function**: `Spaceport-WaitlistFunction`
   - Runtime: Python 3.9
   - Handles form validation, duplicate checking, and data storage
   - Sends admin notifications via SES

3. **API Gateway**: `/waitlist` endpoint
   - Method: POST
   - CORS enabled
   - Integrated with Lambda function

4. **Frontend Integration**
   - Clean form with pill-shaped inputs
   - Loading states and error handling
   - Success confirmation

## Data Structure

### DynamoDB Item Schema

```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "timestamp": "2025-08-05T22:40:00.000Z",
  "source": "website",
  "status": "active"
}
```

### API Request Format

```json
{
  "name": "John Doe",
  "email": "user@example.com"
}
```

### API Response Format

**Success (200):**
```json
{
  "message": "Successfully added to waitlist",
  "email": "user@example.com"
}
```

**Error (400/409/500):**
```json
{
  "error": "Error message"
}
```

## Features

### Validation
- Required fields: name and email
- Email format validation
- Duplicate email prevention

### Admin Notifications
- Automatic email to `gabriel@spcprt.com`
- Sent from `gabriel@spcprt.com` (verified SES identity)
- Includes name, email, and timestamp
- HTML and text versions

### Error Handling
- Duplicate email detection (409 Conflict)
- Invalid email format (400 Bad Request)
- Server errors (500 Internal Server Error)

### Security
- CORS headers for cross-origin requests
- Input sanitization
- Proper error messages without exposing internals

## Deployment

### Prerequisites
- AWS CDK installed
- AWS credentials configured
- SES verified for `gabriel@spcprt.com` (use: `aws ses verify-email-identity --email-address gabriel@spcprt.com --region us-west-2`)

### Deploy Command
```bash
./scripts/deployment/deploy_waitlist.sh
```

### Manual Deployment
```bash
cd infrastructure/spaceport_cdk
npm install
cdk deploy SpaceportStack --require-approval never
```

## Configuration

### Environment Variables
- `WAITLIST_TABLE_NAME`: DynamoDB table name

### IAM Permissions
The Lambda function has permissions for:
- DynamoDB read/write access to waitlist table
- SES send email permissions
- CloudWatch logging

## Monitoring

### CloudWatch Logs
- Lambda function logs: `/aws/lambda/Spaceport-WaitlistFunction`
- API Gateway logs: Available in CloudWatch

### DynamoDB Metrics
- Monitor table usage and throttling
- Set up CloudWatch alarms for errors

## Testing

### Local Testing
1. Set `WAITLIST_MODE = true` in `index.html`
2. Navigate to Create section
3. Fill out and submit the form
4. Check browser console for API responses

### Production Testing
1. Deploy infrastructure
2. Test form submission
3. Verify DynamoDB entry creation
4. Confirm admin email notification

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Verify API Gateway CORS configuration
   - Check request headers

2. **Email Notifications Not Working**
   - Verify SES is configured for `gabriel@spcprt.com`
   - Check Lambda CloudWatch logs

3. **DynamoDB Errors**
   - Verify table permissions
   - Check table capacity settings

### Debug Steps
1. Check Lambda CloudWatch logs
2. Verify API Gateway integration
3. Test DynamoDB permissions
4. Validate SES configuration

## Future Enhancements

### Potential Improvements
- Email confirmation to users
- Waitlist analytics dashboard
- Export functionality
- Integration with email marketing tools
- A/B testing capabilities

### Scaling Considerations
- DynamoDB auto-scaling
- Lambda concurrency limits
- API Gateway throttling
- SES sending limits 