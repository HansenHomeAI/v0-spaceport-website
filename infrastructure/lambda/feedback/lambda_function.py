import json
import os
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle customer feedback submissions via API Gateway.
    Sends feedback emails to configured recipients using Resend.
    """
    
    # CORS headers
    cors_headers = {
        "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGINS", "*"),
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "POST,OPTIONS"
    }
    
    try:
        # Handle preflight OPTIONS request
        if event.get("httpMethod") == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": ""
            }
        
        # Parse request body
        if "body" not in event:
            raise ValueError("Missing request body")
        
        body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        
        # Validate required fields
        message = body.get("message", "").strip()
        if not message:
            raise ValueError("Feedback message is required")
        
        source = body.get("source", "unknown")
        
        # Get configuration from environment
        resend_api_key = os.environ.get("RESEND_API_KEY")
        if not resend_api_key:
            raise ValueError("RESEND_API_KEY not configured")
        
        recipients = os.environ.get("FEEDBACK_RECIPIENTS", "").split(",")
        recipients = [email.strip() for email in recipients if email.strip()]
        if not recipients:
            raise ValueError("No feedback recipients configured")
        
        from_address = os.environ.get("FEEDBACK_FROM_ADDRESS", "Spaceport <hello@spcprt.com>")
        
        # Import Resend (will be installed via requirements.txt)
        import resend
        
        # Configure Resend client
        resend.api_key = resend_api_key
        
        # Prepare email content
        subject = f"New Feedback from {source.title()}"
        
        # Override recipients for contact-sales
        if source == "contact-sales":
            subject = "New Contact Sales Inquiry"
            recipients = ["jayden@spcprt.com", "gabriel@spcprt.com", "sam@spcprt.com"]
        
        formatted_message = message.replace('\n', '<br>')

        html_content = f"""
        <h2>New Customer Feedback</h2>
        <p><strong>Source:</strong> {source}</p>
        <p><strong>Message:</strong></p>
        <blockquote style="margin: 16px 0; padding: 12px; border-left: 4px solid #E7621E; background-color: #f9f9f9;">
            {formatted_message}
        </blockquote>
        <hr>
        <p style="color: #666; font-size: 12px;">
            Sent via Spaceport Feedback System
        </p>
        """
        
        text_content = f"""
New Customer Feedback

Source: {source}
Message: {message}

---
Sent via Spaceport Feedback System
        """
        
        # Send email to all recipients
        for recipient in recipients:
            try:
                response = resend.Emails.send({
                    "from": from_address,
                    "to": recipient,
                    "subject": subject,
                    "html": html_content,
                    "text": text_content
                })
                logger.info(f"Email sent successfully to {recipient}: {response}")
            except Exception as e:
                logger.error(f"Failed to send email to {recipient}: {str(e)}")
                # Continue trying other recipients
        
        # Log the feedback for monitoring
        logger.info(f"Feedback processed - Source: {source}, Recipients: {len(recipients)}")
        
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps({
                "success": True,
                "message": "Feedback sent successfully"
            })
        }
        
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        return {
            "statusCode": 400,
            "headers": cors_headers,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({
                "success": False,
                "error": "Internal server error"
            })
        }
