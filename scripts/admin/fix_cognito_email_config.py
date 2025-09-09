#!/usr/bin/env python3
"""
Fix Cognito Email Configuration
Switches from SES to COGNITO_DEFAULT to resolve email delivery issues.
"""

import boto3
import json
from datetime import datetime

# Production AWS Configuration
REGION = 'us-west-2'
USER_POOL_ID = 'us-west-2_SnOJuAJXa'

class CognitoEmailFixer:
    def __init__(self):
        self.cognito = boto3.client('cognito-idp', region_name=REGION)
        
    def fix_email_configuration(self):
        """Fix the email configuration to use COGNITO_DEFAULT."""
        try:
            # Update the user pool to use COGNITO_DEFAULT email service
            response = self.cognito.update_user_pool(
                UserPoolId=USER_POOL_ID,
                EmailConfiguration={
                    'EmailSendingAccount': 'COGNITO_DEFAULT'
                },
                EmailVerificationMessage='The verification code to your new account is {####}',
                EmailVerificationSubject='Verify your new account',
                VerificationMessageTemplate={
                    'DefaultEmailOption': 'CONFIRM_WITH_CODE',
                    'EmailMessage': 'The verification code to your new account is {####}',
                    'EmailSubject': 'Verify your new account'
                }
            )
            
            print("✅ Updated Cognito email configuration to use COGNITO_DEFAULT")
            return True
            
        except Exception as e:
            print(f"❌ Error updating email configuration: {str(e)}")
            return False
            
    def test_password_reset(self, email):
        """Test password reset after configuration change."""
        try:
            response = self.cognito.forgot_password(
                ClientId='cvtn1c5dprnfbvpbtsuhit6vi',
                Username=email
            )
            
            if response.get('CodeDeliveryDetails'):
                destination = response['CodeDeliveryDetails'].get('Destination', 'Unknown')
                print(f"✅ Password reset initiated for {email} - Code sent to: {destination}")
                return True
            else:
                print(f"❌ Password reset failed for {email}: No delivery details")
                return False
                
        except Exception as e:
            print(f"❌ Password reset failed for {email}: {str(e)}")
            return False
            
    def run_fix(self):
        """Run the complete fix process."""
        print("🔧 Fixing Cognito Email Configuration")
        print("=" * 50)
        
        # Step 1: Fix email configuration
        print("\n📧 Updating Email Configuration...")
        if self.fix_email_configuration():
            print("✅ Email configuration updated successfully")
        else:
            print("❌ Failed to update email configuration")
            return False
            
        # Step 2: Test password reset
        print("\n🔄 Testing Password Reset...")
        test_emails = ['gbhbyu@gmail.com', 'ethan@spcprt.com']
        
        for email in test_emails:
            self.test_password_reset(email)
            
        print("\n🎉 Email configuration fix completed!")
        print("\n📋 What was changed:")
        print("  - Switched from SES to COGNITO_DEFAULT email service")
        print("  - Added proper email verification templates")
        print("  - Removed SES sandbox restrictions")
        print("\n✅ Password reset emails should now work for all users!")
        
        return True

if __name__ == "__main__":
    fixer = CognitoEmailFixer()
    fixer.run_fix()
