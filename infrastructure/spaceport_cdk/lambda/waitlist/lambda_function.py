import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ['WAITLIST_TABLE_NAME']
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    """
    Handle waitlist submissions and store them in DynamoDB
    """
    
    # Handle OPTIONS request for CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({'message': 'CORS preflight'})
        }
    
    try:
        # Parse the request body
        if isinstance(event['body'], str):
            body = json.loads(event['body'])
        else:
            body = event['body']
        
        # Extract data from the request
        name = body.get('name', '').strip()
        email = body.get('email', '').strip().lower()
        
        # Validate required fields
        if not name or not email:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS',
                    'Access-Control-Allow-Credentials': 'true'
                },
                'body': json.dumps({
                    'error': 'Name and email are required'
                })
            }
        
        # Basic email validation
        if '@' not in email or '.' not in email:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS',
                    'Access-Control-Allow-Credentials': 'true'
                },
                'body': json.dumps({
                    'error': 'Please provide a valid email address'
                })
            }
        
        # Allow multiple entries with the same email for testing purposes
        # Commented out duplicate check to allow repeated testing
        # try:
        #     response = table.get_item(
        #         Key={
        #             'email': email
        #         }
        #     )
        #     
        #     if 'Item' in response:
        #         return {
        #             'statusCode': 409,
        #             'headers': {
        #                 'Access-Control-Allow-Origin': '*',
        #                 'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
        #                 'Access-Control-Allow-Methods': 'POST,OPTIONS',
        #                 'Access-Control-Allow-Credentials': 'true'
        #             },
        #             'body': json.dumps({
        #                 'error': 'This email is already on the waitlist'
        #             })
        #         }
        # except ClientError as e:
        #     print(f"Error checking existing email: {e}")
        
        # Create timestamp
        timestamp = datetime.utcnow().isoformat()
        
        # Store in DynamoDB
        item = {
            'email': email,
            'name': name,
            'timestamp': timestamp,
            'source': 'website',
            'status': 'active'
        }
        
        table.put_item(Item=item)
        
        # Send confirmation email to the user
        try:
            send_confirmation_email(name, email)
        except Exception as e:
            print(f"Failed to send confirmation email: {e}")
            # Don't fail the request if confirmation email fails
        
        # Optional: Send notification email to admin
        try:
            send_admin_notification(name, email)
        except Exception as e:
            print(f"Failed to send admin notification: {e}")
            # Don't fail the request if notification fails
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({
                'message': 'Successfully added to waitlist',
                'email': email
            })
        }
        
    except Exception as e:
        print(f"Error processing waitlist submission: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({
                'error': 'Internal server error'
            })
        }

def send_confirmation_email(name, email):
    """
    Send confirmation email to new waitlist signup
    """
    ses = boto3.client('ses')
    
    subject = 'Welcome to Spaceport AI - You\'re on the Waitlist!'
    
    body_text = f"""Hi {name},

This is Gabriel, the founder of Spaceport AI. On behalf of our team, thanks for signing up for our waitlist!

You'll be among the first to know when we launch and get early access to our features. If selected, you'll have the option to become one of our early beta users.

Stay tuned for updates by following our socials!

Best regards,

Gabriel Hansen
Founder, CEO
Spaceport AI

Follow us:
Instagram: https://instagram.com/Spaceport_AI
Facebook: https://www.facebook.com/profile.php?id=61578856815066
LinkedIn: https://www.linkedin.com/company/spaceport-ai/

---
You can unsubscribe from these emails by replying with "unsubscribe"."""

    body_html = f"""<html>
<head>
    <style>
        body {{ font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f7; }}
        .container {{ background: white; border-radius: 25px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
        .logo {{ text-align: center; padding: 40px 30px 20px; }}
        .logo svg {{ max-width: 350px; height: auto; }}
        .content {{ padding: 30px; text-align: left; }}
        .signature {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e5e7; }}
        .social-links {{
            margin: 30px 0;
            text-align: center;
            display: flex;
            justify-content: center;
            gap: 20px;
        }}
        .social-icon-link {{
            display: inline-block;
            padding: 12px;
            border-radius: 50%;
            background: #000000;
            text-decoration: none;
            transition: transform 0.2s ease;
            width: 44px;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .social-icon-link:hover {{
            transform: scale(1.1);
        }}
        .social-icon {{
            width: 20px;
            height: 20px;
            fill: white;
        }}
        .footer {{ padding: 20px 30px; font-size: 12px; color: #86868b; text-align: center; background-color: #f5f5f7; }}
        h1 {{ font-size: 28px; font-weight: 500; margin: 0 0 10px 0; color: #1d1d1f; }}
        p {{ margin: 0 0 16px 0; color: #1d1d1f; font-weight: 400; }}
        ul {{ margin: 16px 0; padding-left: 20px; }}
        li {{ margin: 8px 0; color: #1d1d1f; font-weight: 400; }}
        strong {{ font-weight: 500; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <svg width="2378" height="372" viewBox="0 0 2378 372" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M93.0965 37.3018C93.3099 39.4351 94.1205 40.9285 95.5285 41.7818C96.9365 42.6351 98.6219 43.0618 100.585 43.0618C101.267 43.0618 102.035 43.0191 102.889 42.9338C103.785 42.8058 104.617 42.5925 105.385 42.2938C106.153 41.9951 106.771 41.5685 107.241 41.0138C107.753 40.4165 107.987 39.6485 107.945 38.7098C107.902 37.7711 107.561 37.0031 106.921 36.4058C106.281 35.8085 105.449 35.3391 104.425 34.9978C103.443 34.6138 102.313 34.2938 101.033 34.0378C99.7525 33.7818 98.4512 33.5045 97.1285 33.2058C95.7632 32.9071 94.4405 32.5445 93.1605 32.1178C91.9232 31.6911 90.7925 31.1151 89.7685 30.3898C88.7872 29.6645 87.9979 28.7471 87.4005 27.6378C86.8032 26.4858 86.5045 25.0778 86.5045 23.4138C86.5045 21.6218 86.9312 20.1285 87.7845 18.9338C88.6805 17.6965 89.7899 16.7151 91.1125 15.9898C92.4779 15.2218 93.9712 14.6885 95.5925 14.3898C97.2565 14.0911 98.8352 13.9418 100.329 13.9418C102.035 13.9418 103.657 14.1338 105.193 14.5178C106.771 14.8591 108.179 15.4351 109.417 16.2458C110.697 17.0565 111.742 18.1231 112.553 19.4458C113.406 20.7258 113.939 22.2831 114.153 24.1178H106.537C106.195 22.3685 105.385 21.1951 104.105 20.5978C102.867 20.0005 101.438 19.7018 99.8165 19.7018C99.3045 19.7018 98.6859 19.7445 97.9605 19.8298C97.2779 19.9151 96.6165 20.0858 95.9765 20.3418C95.3792 20.5551 94.8672 20.8965 94.4405 21.3658C94.0139 21.7925 93.8005 22.3685 93.8005 23.0938C93.8005 23.9898 94.0992 24.7151 94.6965 25.2698C95.3365 25.8245 96.1472 26.2938 97.1285 26.6778C98.1525 27.0191 99.3045 27.3178 100.585 27.5738C101.865 27.8298 103.187 28.1071 104.553 28.4058C105.875 28.7045 107.177 29.0671 108.457 29.4938C109.737 29.9205 110.867 30.4965 111.849 31.2218C112.873 31.9471 113.683 32.8645 114.281 33.9738C114.921 35.0831 115.241 36.4485 115.241 38.0698C115.241 40.0325 114.793 41.6965 113.897 43.0618C113.001 44.4271 111.827 45.5365 110.377 46.3898C108.969 47.2431 107.39 47.8618 105.641 48.2458C103.891 48.6298 102.163 48.8218 100.457 48.8218C98.3659 48.8218 96.4245 48.5871 94.6325 48.1178C92.8832 47.6485 91.3472 46.9445 90.0245 46.0058C88.7445 45.0245 87.7205 43.8298 86.9525 42.4218C86.2272 40.9711 85.8432 39.2645 85.8005 37.3018H93.0965Z" fill="white"/>
                <path d="M120.972 14.8378H127.884V19.3178H128.012C129.036 17.3978 130.465 16.0325 132.3 15.2218C134.135 14.3685 136.119 13.9418 138.252 13.9418C140.855 13.9418 143.116 14.4111 145.036 15.3498C146.999 16.2458 148.62 17.5045 149.9 19.1258C151.18 20.7045 152.14 22.5605 152.78 24.6938C153.42 26.8271 153.74 29.1098 153.74 31.5418C153.74 33.7605 153.441 35.9151 152.844 38.0058C152.289 40.0965 151.415 41.9525 150.22 43.5738C149.068 45.1525 147.596 46.4325 145.804 47.4138C144.012 48.3525 141.9 48.8218 139.468 48.8218C138.401 48.8218 137.335 48.7151 136.268 48.5018C135.201 48.3311 134.177 48.0325 133.196 47.6058C132.215 47.1791 131.297 46.6458 130.444 46.0058C129.633 45.3231 128.951 44.5338 128.396 43.6378H128.268V60.1498H120.972V14.8378ZM146.444 31.4138C146.444 29.9205 146.252 28.4698 145.868 27.0618C145.484 25.6538 144.908 24.4165 144.14 23.3498C143.372 22.2405 142.412 21.3658 141.26 20.7258C140.108 20.0431 138.785 19.7018 137.292 19.7018C134.22 19.7018 131.895 20.7685 130.316 22.9018C128.78 25.0351 128.012 27.8725 128.012 31.4138C128.012 33.0778 128.204 34.6351 128.588 36.0858C129.015 37.4938 129.633 38.7098 130.444 39.7338C131.255 40.7578 132.215 41.5685 133.324 42.1658C134.476 42.7631 135.799 43.0618 137.292 43.0618C138.956 43.0618 140.364 42.7205 141.516 42.0378C142.668 41.3551 143.607 40.4805 144.332 39.4138C145.1 38.3045 145.633 37.0671 145.932 35.7018C146.273 34.2938 146.444 32.8645 146.444 31.4138Z" fill="white"/>
                <path d="M187.617 40.5658C187.617 41.4618 187.724 42.1018 187.937 42.4858C188.193 42.8698 188.662 43.0618 189.345 43.0618C189.558 43.0618 189.814 43.0618 190.113 43.0618C190.412 43.0618 190.753 43.0191 191.137 42.9338V47.9898C190.881 48.0751 190.54 48.1605 190.113 48.2458C189.729 48.3738 189.324 48.4805 188.897 48.5658C188.47 48.6511 188.044 48.7151 187.617 48.7578C187.19 48.8005 186.828 48.8218 186.529 48.8218C185.036 48.8218 183.798 48.5231 182.817 47.9258C181.836 47.3285 181.196 46.2831 180.897 44.7898C179.446 46.1978 177.654 47.2218 175.521 47.8618C173.43 48.5018 171.404 48.8218 169.441 48.8218C167.948 48.8218 166.518 48.6085 165.153 48.1818C163.788 47.7978 162.572 47.2218 161.505 46.4538C160.481 45.6431 159.649 44.6405 159.009 43.4458C158.412 42.2085 158.113 40.7791 158.113 39.1578C158.113 37.1098 158.476 35.4458 159.201 34.1658C159.969 32.8858 160.95 31.8831 162.145 31.1578C163.382 30.4325 164.748 29.9205 166.241 29.6218C167.777 29.2805 169.313 29.0245 170.849 28.8538C172.172 28.5978 173.43 28.4271 174.625 28.3418C175.82 28.2138 176.865 28.0218 177.761 27.7658C178.7 27.5098 179.425 27.1258 179.937 26.6138C180.492 26.0591 180.769 25.2485 180.769 24.1818C180.769 23.2431 180.534 22.4751 180.065 21.8778C179.638 21.2805 179.084 20.8325 178.401 20.5338C177.761 20.1925 177.036 19.9791 176.225 19.8938C175.414 19.7658 174.646 19.7018 173.921 19.7018C171.873 19.7018 170.188 20.1285 168.865 20.9818C167.542 21.8351 166.796 23.1578 166.625 24.9498H159.329C159.457 22.8165 159.969 21.0458 160.865 19.6378C161.761 18.2298 162.892 17.0991 164.257 16.2458C165.665 15.3925 167.244 14.7951 168.993 14.4538C170.742 14.1125 172.534 13.9418 174.369 13.9418C175.99 13.9418 177.59 14.1125 179.169 14.4538C180.748 14.7951 182.156 15.3498 183.393 16.1178C184.673 16.8858 185.697 17.8885 186.465 19.1258C187.233 20.3205 187.617 21.7925 187.617 23.5418V40.5658ZM180.321 31.3498C179.212 32.0751 177.846 32.5231 176.225 32.6938C174.604 32.8218 172.982 33.0351 171.361 33.3338C170.593 33.4618 169.846 33.6538 169.121 33.9098C168.396 34.1231 167.756 34.4431 167.201 34.8698C166.646 35.2538 166.198 35.7871 165.857 36.4698C165.558 37.1098 165.409 37.8991 165.409 38.8378C165.409 39.6485 165.644 40.3311 166.113 40.8858C166.582 41.4405 167.137 41.8885 167.777 42.2298C168.46 42.5285 169.185 42.7418 169.953 42.8698C170.764 42.9978 171.489 43.0618 172.129 43.0618C172.94 43.0618 173.814 42.9551 174.753 42.7418C175.692 42.5285 176.566 42.1658 177.377 41.6538C178.23 41.1418 178.934 40.5018 179.489 39.7338C180.044 38.9231 180.321 37.9418 180.321 36.7898V31.3498Z" fill="white"/>
                <path d="M217.804 25.9098C217.505 23.8618 216.673 22.3258 215.308 21.3018C213.985 20.2351 212.3 19.7018 210.252 19.7018C209.313 19.7018 208.31 19.8725 207.244 20.2138C206.177 20.5125 205.196 21.1098 204.3 22.0058C203.404 22.8591 202.657 24.0751 202.06 25.6538C201.462 27.1898 201.164 29.2165 201.164 31.7338C201.164 33.0991 201.313 34.4645 201.612 35.8298C201.953 37.1951 202.465 38.4111 203.148 39.4778C203.873 40.5445 204.79 41.4191 205.9 42.1018C207.009 42.7418 208.353 43.0618 209.932 43.0618C212.065 43.0618 213.814 42.4005 215.18 41.0778C216.588 39.7551 217.462 37.8991 217.804 35.5098H225.1C224.417 39.8191 222.774 43.1258 220.172 45.4298C217.612 47.6911 214.198 48.8218 209.932 48.8218C207.329 48.8218 205.025 48.3951 203.02 47.5418C201.057 46.6458 199.393 45.4511 198.028 43.9578C196.662 42.4218 195.617 40.6085 194.892 38.5178C194.209 36.4271 193.868 34.1658 193.868 31.7338C193.868 29.2591 194.209 26.9338 194.892 24.7578C195.574 22.5818 196.598 20.7045 197.964 19.1258C199.329 17.5045 201.014 16.2458 203.02 15.3498C205.068 14.4111 207.457 13.9418 210.188 13.9418C212.108 13.9418 213.921 14.1978 215.628 14.7098C217.377 15.1791 218.913 15.9045 220.236 16.8858C221.601 17.8671 222.71 19.1045 223.564 20.5978C224.417 22.0911 224.929 23.8618 225.1 25.9098H217.804Z" fill="white"/>
                <path d="M253.75 28.4698C253.665 27.3178 253.409 26.2085 252.982 25.1418C252.598 24.0751 252.043 23.1578 251.318 22.3898C250.635 21.5791 249.782 20.9391 248.758 20.4698C247.777 19.9578 246.667 19.7018 245.43 19.7018C244.15 19.7018 242.977 19.9365 241.91 20.4058C240.886 20.8325 239.99 21.4511 239.222 22.2618C238.497 23.0298 237.899 23.9471 237.43 25.0138C237.003 26.0805 236.769 27.2325 236.726 28.4698H253.75ZM236.726 33.2698C236.726 34.5498 236.897 35.7871 237.238 36.9818C237.622 38.1765 238.177 39.2218 238.902 40.1178C239.627 41.0138 240.545 41.7391 241.654 42.2938C242.763 42.8058 244.086 43.0618 245.622 43.0618C247.755 43.0618 249.462 42.6138 250.742 41.7178C252.065 40.7791 253.046 39.3925 253.686 37.5578H260.598C260.214 39.3498 259.553 40.9498 258.614 42.3578C257.675 43.7658 256.545 44.9605 255.222 45.9418C253.899 46.8805 252.406 47.5845 250.742 48.0538C249.121 48.5658 247.414 48.8218 245.622 48.8218C243.019 48.8218 240.715 48.3951 238.71 47.5418C236.705 46.6885 234.998 45.4938 233.59 43.9578C232.225 42.4218 231.179 40.5871 230.454 38.4538C229.771 36.3205 229.43 33.9738 229.43 31.4138C229.43 29.0671 229.793 26.8485 230.518 24.7578C231.286 22.6245 232.353 20.7685 233.718 19.1898C235.126 17.5685 236.811 16.2885 238.774 15.3498C240.737 14.4111 242.955 13.9418 245.43 13.9418C248.033 13.9418 250.358 14.4965 252.406 15.6058C254.497 16.6725 256.225 18.1018 257.59 19.8938C258.955 21.6858 259.937 23.7551 260.534 26.1018C261.174 28.4058 261.345 30.7951 261.046 33.2698H236.726Z" fill="white"/>
                <path d="M266.785 14.8378H273.697V19.3178H273.825C274.849 17.3978 276.278 16.0325 278.113 15.2218C279.947 14.3685 281.931 13.9418 284.065 13.9418C286.667 13.9418 288.929 14.4111 290.849 15.3498C292.811 16.2458 294.433 17.5045 295.713 19.1258C296.993 20.7045 297.953 22.5605 298.593 24.6938C299.233 26.8271 299.553 29.1098 299.553 31.5418C299.553 33.7605 299.254 35.9151 298.657 38.0058C298.102 40.0965 297.227 41.9525 296.033 43.5738C294.881 45.1525 293.409 46.4325 291.617 47.4138C289.825 48.3525 287.713 48.8218 285.281 48.8218C284.214 48.8218 283.147 48.7151 282.081 48.5018C281.014 48.3311 279.99 48.0325 279.009 47.6058C278.027 47.1791 277.11 46.6458 276.257 46.0058C275.446 45.3231 274.763 44.5338 274.209 43.6378H274.081V60.1498H266.785V14.8378ZM292.257 31.4138C292.257 29.9205 292.065 28.4698 291.681 27.0618C291.297 25.6538 290.721 24.4165 289.953 23.3498C289.185 22.2405 288.225 21.3658 287.073 20.7258C285.921 20.0431 284.598 19.7018 283.105 19.7018C280.033 19.7018 277.707 20.7685 276.129 22.9018C274.593 25.0351 273.825 27.8725 273.825 31.4138C273.825 33.0778 274.017 34.6351 274.401 36.0858C274.827 37.4938 275.446 38.7098 276.257 39.7338C277.067 40.7578 278.027 41.5685 279.137 42.1658C280.289 42.7631 281.611 43.0618 283.105 43.0618C284.769 43.0618 286.177 42.7205 287.329 42.0378C288.481 41.3551 289.419 40.4805 290.145 39.4138C290.913 38.3045 291.446 37.0671 291.745 35.7018C292.086 34.2938 292.257 32.8645 292.257 31.4138Z" fill="white"/>
                <path d="M320.886 48.8218C318.24 48.8218 315.872 48.3951 313.782 47.5418C311.734 46.6458 309.984 45.4298 308.534 43.8938C307.126 42.3578 306.038 40.5231 305.27 38.3898C304.544 36.2565 304.182 33.9098 304.182 31.3498C304.182 28.8325 304.544 26.5071 305.27 24.3738C306.038 22.2405 307.126 20.4058 308.534 18.8698C309.984 17.3338 311.734 16.1391 313.782 15.2858C315.872 14.3898 318.24 13.9418 320.886 13.9418C323.531 13.9418 325.878 14.3898 327.926 15.2858C330.016 16.1391 331.766 17.3338 333.174 18.8698C334.624 20.4058 335.712 22.2405 336.438 24.3738C337.206 26.5071 337.59 28.8325 337.59 31.3498C337.59 33.9098 337.206 36.2565 336.438 38.3898C335.712 40.5231 334.624 42.3578 333.174 43.8938C331.766 45.4298 330.016 46.6458 327.926 47.5418C325.878 48.3951 323.531 48.8218 320.886 48.8218ZM320.886 43.0618C322.507 43.0618 323.915 42.7205 325.11 42.0378C326.304 41.3551 327.286 40.4591 328.054 39.3498C328.822 38.2405 329.376 37.0031 329.718 35.6378C330.102 34.2298 330.294 32.8005 330.294 31.3498C330.294 29.9418 330.102 28.5338 329.718 27.1258C329.376 25.7178 328.822 24.4805 328.054 23.4138C327.286 22.3045 326.304 21.4085 325.11 20.7258C323.915 20.0431 322.507 19.7018 320.886 19.7018C319.264 19.7018 317.856 20.0431 316.662 20.7258C315.467 21.4085 314.486 22.3045 313.718 23.4138C312.95 24.4805 312.374 25.7178 311.99 27.1258C311.648 28.5338 311.478 29.9418 311.478 31.3498C311.478 32.8005 311.648 34.2298 311.99 35.6378C312.374 37.0031 312.95 38.2405 313.718 39.3498C314.486 40.4591 315.467 41.3551 316.662 42.0378C317.856 42.7205 319.264 43.0618 320.886 43.0618Z" fill="white"/>
                <path d="M343.655 14.8378H350.503V21.2378H350.631C350.844 20.3418 351.25 19.4671 351.847 18.6138C352.487 17.7605 353.234 16.9925 354.087 16.3098C354.983 15.5845 355.964 15.0085 357.031 14.5818C358.098 14.1551 359.186 13.9418 360.295 13.9418C361.148 13.9418 361.724 13.9631 362.023 14.0058C362.364 14.0485 362.706 14.0911 363.047 14.1338V21.1738C362.535 21.0885 362.002 21.0245 361.447 20.9818C360.935 20.8965 360.423 20.8538 359.911 20.8538C358.674 20.8538 357.5 21.1098 356.391 21.6218C355.324 22.0911 354.386 22.8165 353.575 23.7978C352.764 24.7365 352.124 25.9098 351.655 27.3178C351.186 28.7258 350.951 30.3471 350.951 32.1818V47.9258H343.655V14.8378Z" fill="white"/>
                <path d="M366.167 14.8378H371.671V4.91779H378.967V14.8378H385.559V20.2778H378.967V37.9418C378.967 38.7098 378.988 39.3711 379.031 39.9258C379.116 40.4805 379.266 40.9498 379.479 41.3338C379.735 41.7178 380.098 42.0165 380.567 42.2298C381.036 42.4005 381.676 42.4858 382.487 42.4858C382.999 42.4858 383.511 42.4858 384.023 42.4858C384.535 42.4431 385.047 42.3578 385.559 42.2298V47.8618C384.748 47.9471 383.959 48.0325 383.191 48.1178C382.423 48.2031 381.634 48.2458 380.823 48.2458C378.903 48.2458 377.346 48.0751 376.151 47.7338C374.999 47.3498 374.082 46.8165 373.399 46.1338C372.759 45.4085 372.311 44.5125 372.055 43.4458C371.842 42.3791 371.714 41.1631 371.671 39.7978V20.2778H366.167V14.8378Z" fill="white"/>
                <path fill-rule="evenodd" clip-rule="evenodd" d="M46.2168 0.404297C53.9488 0.404298 60.2168 6.67231 60.2168 14.4043V46.498C60.2168 54.23 53.9488 60.498 46.2168 60.498H14.123C6.39106 60.498 0.123047 54.23 0.123047 46.498V14.4043C0.123048 6.67231 6.39106 0.404297 14.123 0.404297H46.2168ZM37.376 16.5566C34.1552 11.3732 26.6793 11.2925 23.3252 16.3135L23.168 16.5566L7.01562 42.5527C6.31387 43.6823 6.28311 45.0466 6.65918 46.1201C7.02444 47.162 8.73572 48.2948 10.2002 48.2949H14.5557C21.9966 48.2946 27.7429 42.3716 28.6436 33.5254L28.665 33.3818C28.8001 32.6791 29.3731 32.211 29.9639 32.2109H30.5801C31.21 32.2113 31.8196 32.7436 31.8994 33.5254L31.9453 33.9375C32.9802 42.5552 38.6632 48.2949 45.9883 48.2949H50.3438C51.808 48.2945 53.5195 47.1618 53.8848 46.1201C54.2372 45.1138 54.2315 43.852 53.6514 42.7676L53.5283 42.5527L37.376 16.5566Z" fill="#CD70E4"/>
            </svg>
        </div>
        
        <div class="content">
            <p>Hi {name},</p>
            
            <p>This is Gabriel, the founder of Spaceport AI. On behalf of our team, thanks for signing up for our waitlist!</p>
            
            <p>You'll be among the first to know when we launch and get early access to our features. If selected, you'll have the option to become one of our early beta users.</p>
            
            <p><strong>Stay tuned for updates by following our socials!</strong></p>
            
            <div class="signature">
                <p><strong>Best regards,</strong></p>
                <p>Gabriel Hansen<br>
                Founder, CEO<br>
                Spaceport AI</p>
            </div>
            
            <div class="social-links">
                <a href="https://instagram.com/Spaceport_AI" class="social-icon-link">
                    <img src="https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/instagram.svg" alt="Instagram" class="social-icon" style="filter: invert(1);">
                </a>
                
                <a href="https://www.facebook.com/profile.php?id=61578856815066" class="social-icon-link">
                    <img src="https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/facebook.svg" alt="Facebook" class="social-icon" style="filter: invert(1);">
                </a>
                
                <a href="https://www.linkedin.com/company/spaceport-ai/" class="social-icon-link">
                    <img src="https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/linkedin.svg" alt="LinkedIn" class="social-icon" style="filter: invert(1);">
                </a>
            </div>
        </div>
        
        <div class="footer">
            <p>You can unsubscribe from these emails by replying with "unsubscribe".</p>
        </div>
    </div>
</body>
</html>"""

    try:
        response = ses.send_email(
            Source='gabriel@spcprt.com',
            Destination={
                'ToAddresses': [email]
            },
            Message={
                'Subject': {
                    'Data': subject
                },
                'Body': {
                    'Text': {
                        'Data': body_text
                    },
                    'Html': {
                        'Data': body_html
                    }
                }
            }
        )
        print(f"Confirmation email sent to {email}: {response['MessageId']}")
    except ClientError as e:
        print(f"Failed to send confirmation email to {email}: {e}")
        raise

def send_admin_notification(name, email):
    """
    Send notification email to admin about new waitlist signup
    """
    ses = boto3.client('ses')
    
    subject = 'New Waitlist Signup - Spaceport AI'
    body_text = f"""New waitlist signup:
    
Name: {name}
Email: {email}
Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

This person will be notified when Spaceport AI launches."""

    body_html = f"""<html>
<head></head>
<body>
    <h2>New Waitlist Signup</h2>
    <p><strong>Name:</strong> {name}</p>
    <p><strong>Email:</strong> {email}</p>
    <p><strong>Date:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    <p>This person will be notified when Spaceport AI launches.</p>
</body>
</html>"""

    try:
        response = ses.send_email(
            Source='gabriel@spcprt.com',  # Your preferred email address
            Destination={
                'ToAddresses': ['gabriel@spcprt.com']
            },
            Message={
                'Subject': {
                    'Data': subject
                },
                'Body': {
                    'Text': {
                        'Data': body_text
                    },
                    'Html': {
                        'Data': body_html
                    }
                }
            }
        )
        print(f"Admin notification sent: {response['MessageId']}")
    except ClientError as e:
        print(f"Failed to send admin notification: {e}")
        raise 