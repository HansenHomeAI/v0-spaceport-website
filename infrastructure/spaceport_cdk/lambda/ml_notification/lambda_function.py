import json
import boto3
import os
from datetime import datetime

# Initialize AWS clients
ses = boto3.client('ses')

def lambda_handler(event, context):
    """
    Lambda function to send notifications about ML processing status
    """
    
    try:
        # Extract data from Step Functions payload
        job_id = event.get('jobId')
        email = event.get('email', 'hello@spcprt.com')
        s3_url = event.get('s3Url')
        status = event.get('status')  # 'completed' or 'failed'
        compressed_output_uri = event.get('compressedOutputS3Uri')
        
        # Handle different error sources - new approach with state object
        state = event.get('state', {})
        
        # Extract error message from different possible sources
        actual_error = None
        
        # Check for catch block errors ($.error.Cause)
        if 'error' in state and 'Cause' in state['error']:
            actual_error = state['error']['Cause']
        
        # Check for SfM processing errors
        elif 'sfmStatus' in state and 'FailureReason' in state['sfmStatus']:
            actual_error = state['sfmStatus']['FailureReason']
        
        # Check for Gaussian training errors
        elif 'gaussianStatus' in state and 'FailureReason' in state['gaussianStatus']:
            actual_error = state['gaussianStatus']['FailureReason']
        
        # Check for compression errors
        elif 'compressionStatus' in state and 'FailureReason' in state['compressionStatus']:
            actual_error = state['compressionStatus']['FailureReason']
        
        # Fallback to legacy error fields for backward compatibility
        else:
            error = event.get('error')
            sfm_error = event.get('sfmError')
            gaussian_error = event.get('gaussianError')
            compression_error = event.get('compressionError')
            actual_error = error or sfm_error or gaussian_error or compression_error
        
        # Final fallback
        if not actual_error:
            actual_error = 'Unknown error occurred during processing'
        
        # Prepare email content based on status
        if status == 'completed':
            subject = "🎉 Your 3D Model is Ready!"
            body_text, body_html = create_success_email(job_id, s3_url, compressed_output_uri)
        elif status == 'failed':
            subject = "❌ 3D Model Processing Failed"
            body_text, body_html = create_failure_email(job_id, s3_url, actual_error)
        else:
            raise ValueError(f"Unknown status: {status}")
        
        # Send email via SES
        response = ses.send_email(
            Source='hello@spcprt.com',  # Using the verified email address
            Destination={
                'ToAddresses': [email]
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': body_text,
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data': body_html,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        
        print(f"Email sent successfully. MessageId: {response['MessageId']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Notification sent successfully',
                'messageId': response['MessageId']
            })
        }
        
    except Exception as e:
        print(f"Error sending notification: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Failed to send notification: {str(e)}'
            })
        }


def create_success_email(job_id, s3_url, compressed_output_uri):
    """Create email content for successful processing"""
    
    body_text = f"""
Your 3D Model is Ready!

Great news! We've successfully processed your drone photos and created your immersive 3D model.

Job ID: {job_id}
Original Upload: {s3_url}
Processed Model: {compressed_output_uri}

Your model has been processed through our advanced pipeline:
1. ✅ Structure from Motion (SfM) processing with COLMAP
2. ✅ 3D Gaussian Splatting training
3. ✅ Model compression for optimal viewing

You can now download your compressed 3D model from the link above. The model is optimized for web viewing and can be embedded in your website or shared with clients.

If you have any questions or need assistance, please don't hesitate to reach out to our support team.

Best regards,
The Spaceport Team
hello@spcprt.com
"""

    body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #FF4F00, #E7621E); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
        .success-icon {{ font-size: 48px; margin-bottom: 20px; }}
        .job-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .step {{ margin: 10px 0; }}
        .step-icon {{ color: #28a745; font-weight: bold; }}
        .download-link {{ background: #FF4F00; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="success-icon">🎉</div>
            <h1>Your 3D Model is Ready!</h1>
        </div>
        <div class="content">
            <p>Great news! We've successfully processed your drone photos and created your immersive 3D model.</p>
            
            <div class="job-details">
                <h3>Processing Details</h3>
                <p><strong>Job ID:</strong> {job_id}</p>
                <p><strong>Original Upload:</strong> <a href="{s3_url}">{s3_url}</a></p>
                <p><strong>Processed Model:</strong> <a href="{compressed_output_uri}">{compressed_output_uri}</a></p>
            </div>
            
            <h3>Processing Pipeline Completed:</h3>
            <div class="step"><span class="step-icon">✅</span> Structure from Motion (SfM) processing with COLMAP</div>
            <div class="step"><span class="step-icon">✅</span> 3D Gaussian Splatting training</div>
            <div class="step"><span class="step-icon">✅</span> Model compression for optimal viewing</div>
            
            <a href="{compressed_output_uri}" class="download-link">Download Your 3D Model</a>
            
            <p>Your model has been optimized for web viewing and can be embedded in your website or shared with clients.</p>
            
            <div class="footer">
                <p>If you have any questions or need assistance, please don't hesitate to reach out to our support team.</p>
                <p><strong>The Spaceport Team</strong><br>
                <a href="mailto:hello@spcprt.com">hello@spcprt.com</a></p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    return body_text, body_html


def create_failure_email(job_id, s3_url, error):
    """Create email content for failed processing"""
    
    body_text = f"""
3D Model Processing Failed

We're sorry, but there was an issue processing your drone photos into a 3D model.

Job ID: {job_id}
Original Upload: {s3_url}
Error: {error or 'Unknown error occurred during processing'}

Our team has been automatically notified of this issue. We'll investigate and reach out to you with next steps.

In the meantime, please check that:
- Your uploaded file is a valid ZIP archive
- The ZIP contains drone photos in a supported format (JPG, PNG)
- The photos have sufficient overlap for 3D reconstruction

If you continue to experience issues, please contact our support team with your Job ID.

Best regards,
The Spaceport Team
hello@spcprt.com
"""

    body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #dc3545, #c82333); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
        .error-icon {{ font-size: 48px; margin-bottom: 20px; }}
        .job-details {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .error-details {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 6px; margin: 20px 0; }}
        .checklist {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .checklist li {{ margin: 8px 0; }}
        .contact-button {{ background: #FF4F00; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="error-icon">❌</div>
            <h1>Processing Failed</h1>
        </div>
        <div class="content">
            <p>We're sorry, but there was an issue processing your drone photos into a 3D model.</p>
            
            <div class="job-details">
                <h3>Job Details</h3>
                <p><strong>Job ID:</strong> {job_id}</p>
                <p><strong>Original Upload:</strong> <a href="{s3_url}">{s3_url}</a></p>
            </div>
            
            <div class="error-details">
                <h4>Error Details:</h4>
                <p>{error or 'Unknown error occurred during processing'}</p>
            </div>
            
            <div class="checklist">
                <h3>Please check that:</h3>
                <ul>
                    <li>Your uploaded file is a valid ZIP archive</li>
                    <li>The ZIP contains drone photos in a supported format (JPG, PNG)</li>
                    <li>The photos have sufficient overlap for 3D reconstruction</li>
                    <li>The photos are high quality and well-lit</li>
                </ul>
            </div>
            
            <p>Our team has been automatically notified of this issue. We'll investigate and reach out to you with next steps.</p>
            
            <a href="mailto:hello@spcprt.com?subject=Processing%20Failed%20-%20Job%20{job_id}" class="contact-button">Contact Support</a>
            
            <div class="footer">
                <p>If you continue to experience issues, please contact our support team with your Job ID.</p>
                <p><strong>The Spaceport Team</strong><br>
                <a href="mailto:hello@spcprt.com">hello@spcprt.com</a></p>
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    return body_text, body_html 