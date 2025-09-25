# app/services/email_service.py - AWS SES Integration with Debug Logging
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any
from app.config import settings
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Set up detailed logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class EmailService:
    def __init__(self):
        logger.info("=== INITIALIZING EMAIL SERVICE ===")
        logger.info(f"AWS Region: {settings.aws_region}")
        logger.info(f"From Email: {settings.from_email}")
        logger.info(f"Support Email: {settings.support_email}")
        
        self.ses_client = boto3.client('sesv2', region_name=settings.aws_region)
        self.from_email = settings.from_email
        self.support_email = settings.support_email
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        logger.info("=== EMAIL SERVICE INITIALIZED SUCCESSFULLY ===")
        
    async def send_welcome_email(
        self, 
        email: str, 
        name: Optional[str] = None,
        subscription_id: str = None
    ) -> bool:
        """Send welcome email to new newsletter subscriber"""
        logger.info("=" * 60)
        logger.info(f"🚀 STARTING WELCOME EMAIL PROCESS")
        logger.info(f"📧 Target Email: {email}")
        logger.info(f"👤 Name: {name}")
        logger.info(f"🆔 Subscription ID: {subscription_id}")
        logger.info("=" * 60)
        
        try:
            # Generate unsubscribe link
            unsubscribe_url = f"{settings.frontend_url}/unsubscribe?id={subscription_id}"
            logger.info(f"🔗 Unsubscribe URL: {unsubscribe_url}")
            
            # Create email content
            subject = "Welcome to Better & Bliss - Your Mental Wellness Journey Starts Here"
            logger.info(f"📝 Email Subject: {subject}")
            
            logger.info("📄 Creating HTML content...")
            html_content = self._create_welcome_email_html(
                name=name or "Friend",
                unsubscribe_url=unsubscribe_url
            )
            logger.info(f"✅ HTML content created (length: {len(html_content)} chars)")
            
            logger.info("📄 Creating text content...")
            text_content = self._create_welcome_email_text(
                name=name or "Friend",
                unsubscribe_url=unsubscribe_url
            )
            logger.info(f"✅ Text content created (length: {len(text_content)} chars)")
            
            logger.info("🚀 Attempting to send email via SES...")
            
            # Send email asynchronously
            result = await self._send_email_async(
                to_email=email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            logger.info(f"✅ SES RESPONSE: {result}")
            logger.info(f"🎉 Welcome email sent successfully to {email}")
            logger.info(f"📬 Message ID: {result.get('message_id', 'N/A')}")
            logger.info("=" * 60)
            return True
            
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"❌ CRITICAL ERROR in send_welcome_email")
            logger.error(f"📧 Email: {email}")
            logger.error(f"🔥 Exception Type: {type(e).__name__}")
            logger.error(f"💬 Exception Message: {str(e)}")
            logger.error(f"📍 Full Exception: {repr(e)}")
            logger.error("=" * 60)
            return False
    
    async def _send_email_async(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email using AWS SES (async wrapper)"""
        logger.info("🔄 Preparing async email send...")
        logger.info(f"📧 TO: {to_email}")
        logger.info(f"📝 SUBJECT: {subject}")
        logger.info(f"📤 FROM: {self.from_email}")
        logger.info(f"↩️ REPLY-TO: {reply_to or self.support_email}")
        
        loop = asyncio.get_event_loop()
        
        logger.info("⚡ Executing SES call in thread pool...")
        
        # Run SES call in thread pool to avoid blocking
        result = await loop.run_in_executor(
            self.executor,
            self._send_email_ses,
            to_email,
            subject,
            html_content,
            text_content,
            reply_to
        )
        
        logger.info(f"🔙 Thread pool execution completed: {result}")
        return result
    
    def _send_email_ses(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email using AWS SES"""
        logger.info("🌐 ENTERING SES EMAIL SEND FUNCTION")
        logger.info(f"📧 TO EMAIL: {to_email}")
        logger.info(f"📤 FROM EMAIL: {self.from_email}")
        logger.info(f"🌍 AWS REGION: {settings.aws_region}")
        
        try:
            logger.info("🔧 Building email parameters...")
            
            email_params = {
                'FromEmailAddress': f"Better & Bliss <{self.from_email}>",
                'Destination': {
                    'ToAddresses': [to_email]
                },
                'Content': {
                    'Simple': {
                        'Subject': {
                            'Data': subject,
                            'Charset': 'UTF-8'
                        },
                        'Body': {
                            'Html': {
                                'Data': html_content,
                                'Charset': 'UTF-8'
                            },
                            'Text': {
                                'Data': text_content,
                                'Charset': 'UTF-8'
                            }
                        }
                    }
                },
                'ReplyToAddresses': [reply_to or self.support_email]
            }
            
            logger.info("✅ Email parameters built successfully")
            logger.info(f"📋 Params structure: {list(email_params.keys())}")
            logger.info(f"📧 Destination: {email_params['Destination']}")
            logger.info(f"📤 From: {email_params['FromEmailAddress']}")
            
            logger.info("🚀 CALLING AWS SES send_email...")
            
            response = self.ses_client.send_email(**email_params)
            
            logger.info("🎊 SES CALL SUCCESSFUL!")
            logger.info(f"📨 Full SES Response: {response}")
            logger.info(f"🆔 Message ID: {response.get('MessageId', 'No Message ID')}")
            
            result = {
                'success': True,
                'message_id': response.get('MessageId'),
                'to_email': to_email
            }
            
            logger.info(f"✅ Returning success result: {result}")
            return result
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            logger.error("🚨 AWS SES CLIENT ERROR!")
            logger.error(f"💥 Error Code: {error_code}")
            logger.error(f"💬 Error Message: {error_message}")
            logger.error(f"📋 Full Error Response: {e.response}")
            logger.error(f"📧 Failed Email: {to_email}")
            
            if error_code == 'MessageRejected':
                raise ValueError(f"Email rejected: {error_message}")
            elif error_code == 'MailFromDomainNotVerified':
                raise ValueError("Sender domain not verified with AWS SES")
            elif error_code == 'SendingPausedException':
                raise ValueError("SES sending is paused - check your account status")
            elif error_code == 'AccountSendingPausedException':
                raise ValueError("Account sending paused - likely due to bounce/complaint rate")
            else:
                raise ValueError(f"Email delivery failed: {error_message}")
                
        except Exception as e:
            logger.error("💀 UNEXPECTED ERROR IN SES SEND!")
            logger.error(f"🔥 Exception Type: {type(e).__name__}")
            logger.error(f"💬 Exception Message: {str(e)}")
            logger.error(f"📍 Full Exception: {repr(e)}")
            logger.error(f"📧 Failed Email: {to_email}")
            raise ValueError(f"Email sending failed: {e}")
    
    def _create_welcome_email_html(self, name: str, unsubscribe_url: str) -> str:
        """Create HTML content for welcome email"""
        logger.info(f"🎨 Creating HTML email for: {name}")
        logger.info(f"🔗 With unsubscribe URL: {unsubscribe_url}")
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to Better & Bliss</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9ff;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(124, 58, 237, 0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .logo {{
                    width: 60px;
                    height: 60px;
                    background: linear-gradient(135deg, #7c3aed, #6366f1);
                    border-radius: 12px;
                    margin: 0 auto 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 24px;
                    font-weight: bold;
                }}
                .title {{
                    color: #7c3aed;
                    font-size: 28px;
                    font-weight: bold;
                    margin: 0;
                }}
                .subtitle {{
                    color: #6b7280;
                    font-size: 16px;
                    margin: 10px 0 0 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">B&B</div>
                    <h1 class="title">Welcome to Better & Bliss!</h1>
                    <p class="subtitle">Your mental wellness journey starts here</p>
                </div>
                
                <p>Hi {name},</p>
                
                <p>Thank you for joining our mental wellness community! This is a test welcome email.</p>
                
                <p>Best regards,<br>The Better & Bliss Team</p>
                
                <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 12px;">
                    <p>Better & Bliss - Mental Health & Wellness Platform</p>
                    <p><a href="{unsubscribe_url}" style="color: #9ca3af; text-decoration: none; font-size: 11px;">Unsubscribe</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        logger.info(f"✅ HTML email created (length: {len(html)} characters)")
        return html
    
    def _create_welcome_email_text(self, name: str, unsubscribe_url: str) -> str:
        """Create plain text content for welcome email"""
        logger.info(f"📝 Creating text email for: {name}")
        
        text = f"""
Welcome to Better & Bliss!

Hi {name},

Thank you for joining our mental wellness community! This is a test welcome email.

Best regards,
The Better & Bliss Team

---
Better & Bliss - Mental Health & Wellness Platform
Unsubscribe: {unsubscribe_url}
        """
        
        logger.info(f"✅ Text email created (length: {len(text)} characters)")
        return text

# Global email service instance
logger.info("🌟 Creating global email service instance...")
email_service = EmailService()
logger.info("🌟 Global email service instance created!")