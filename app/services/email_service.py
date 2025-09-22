# app/services/email_service.py - AWS SES Integration
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any
from app.config import settings
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.ses_client = boto3.client('sesv2', region_name=settings.aws_region)
        self.from_email = settings.from_email
        self.support_email = settings.support_email
        self.executor = ThreadPoolExecutor(max_workers=5)
        
    async def send_welcome_email(
        self, 
        email: str, 
        name: Optional[str] = None,
        subscription_id: str = None
    ) -> bool:
        """Send welcome email to new newsletter subscriber"""
        try:
            # Generate unsubscribe link
            unsubscribe_url = f"{settings.frontend_url}/unsubscribe?id={subscription_id}"
            
            # Create email content
            subject = "Welcome to Better & Bliss - Your Wellness Journey Starts Here!"
            
            html_content = self._create_welcome_email_html(
                name=name or "Friend",
                unsubscribe_url=unsubscribe_url
            )
            
            text_content = self._create_welcome_email_text(
                name=name or "Friend",
                unsubscribe_url=unsubscribe_url
            )
            
            # Send email asynchronously
            await self._send_email_async(
                to_email=email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            logger.info(f"Welcome email sent successfully to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {e}")
            return False
    
    async def send_bulk_newsletter(
        self,
        subject: str,
        html_content: str,
        text_content: str,
        subscriber_emails: list,
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """Send newsletter to multiple subscribers in batches"""
        try:
            total_sent = 0
            failed_emails = []
            
            # Process in batches to avoid rate limits
            for i in range(0, len(subscriber_emails), batch_size):
                batch = subscriber_emails[i:i + batch_size]
                
                # Send batch
                batch_results = await asyncio.gather(
                    *[
                        self._send_email_async(
                            to_email=email,
                            subject=subject,
                            html_content=html_content,
                            text_content=text_content
                        )
                        for email in batch
                    ],
                    return_exceptions=True
                )
                
                # Count results
                for idx, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        failed_emails.append(batch[idx])
                        logger.error(f"Failed to send to {batch[idx]}: {result}")
                    else:
                        total_sent += 1
                
                # Small delay between batches
                if i + batch_size < len(subscriber_emails):
                    await asyncio.sleep(0.1)
            
            logger.info(f"Bulk newsletter sent: {total_sent} successful, {len(failed_emails)} failed")
            
            return {
                'total_sent': total_sent,
                'total_failed': len(failed_emails),
                'failed_emails': failed_emails,
                'success_rate': (total_sent / len(subscriber_emails)) * 100 if subscriber_emails else 0
            }
            
        except Exception as e:
            logger.error(f"Bulk newsletter sending failed: {e}")
            raise
    
    async def _send_email_async(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email using AWS SES (async wrapper)"""
        loop = asyncio.get_event_loop()
        
        # Run SES call in thread pool to avoid blocking
        return await loop.run_in_executor(
            self.executor,
            self._send_email_ses,
            to_email,
            subject,
            html_content,
            text_content,
            reply_to
        )
    
    def _send_email_ses(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email using AWS SES"""
        try:
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
                'ReplyToAddresses': [reply_to or self.support_email],
                'EmailTags': [
                    {
                        'Name': 'EmailType',
                        'Value': 'Newsletter'
                    },
                    {
                        'Name': 'Platform',
                        'Value': 'BetterBliss'
                    }
                ]
            }
            
            # Add configuration set if specified
            if hasattr(settings, 'ses_configuration_set') and settings.ses_configuration_set:
                email_params['ConfigurationSetName'] = settings.ses_configuration_set
            
            response = self.ses_client.send_email(**email_params)
            
            return {
                'success': True,
                'message_id': response.get('MessageId'),
                'to_email': to_email
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            logger.error(f"SES error sending to {to_email}: {error_code} - {error_message}")
            
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
            logger.error(f"Unexpected error sending email to {to_email}: {e}")
            raise ValueError(f"Email sending failed: {e}")

    def _create_welcome_email_html(self, name: str, unsubscribe_url: str) -> str:
        """Create HTML content for welcome email"""
        return f"""
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
                .content {{
                    margin: 30px 0;
                }}
                .highlight-box {{
                    background: linear-gradient(135deg, #f3f4f6, #e5e7eb);
                    padding: 20px;
                    border-radius: 8px;
                    border-left: 4px solid #7c3aed;
                    margin: 20px 0;
                }}
                .benefits {{
                    list-style: none;
                    padding: 0;
                }}
                .benefits li {{
                    padding: 8px 0;
                    border-bottom: 1px solid #f1f5f9;
                }}
                .benefits li:before {{
                    content: "✓";
                    color: #10b981;
                    font-weight: bold;
                    margin-right: 10px;
                }}
                .cta-button {{
                    display: inline-block;
                    background: linear-gradient(135deg, #7c3aed, #6366f1);
                    color: white;
                    padding: 12px 24px;
                    border-radius: 8px;
                    text-decoration: none;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                    color: #6b7280;
                    font-size: 12px;
                }}
                .unsubscribe {{
                    color: #9ca3af;
                    text-decoration: none;
                    font-size: 11px;
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
                
                <div class="content">
                    <p>Hi {name},</p>
                    
                    <p>Thank you for joining our wellness community! We're thrilled to have you on this journey toward better mental health and personal growth.</p>
                    
                    <div class="highlight-box">
                        <h3>What you can expect:</h3>
                        <ul class="benefits">
                            <li>Weekly wellness tips from licensed mental health professionals</li>
                            <li>Practical exercises for stress management and mindfulness</li>
                            <li>Expert insights on anxiety, depression, and emotional wellness</li>
                            <li>Early access to new content and features</li>
                            <li>Supportive community resources</li>
                        </ul>
                    </div>
                    
                    <p>Our mission is to make mental health resources accessible, practical, and stigma-free. Every email we send is designed to provide you with actionable insights that can make a real difference in your daily life.</p>
                    
                    <div style="text-align: center;">
                        <a href="{settings.frontend_url}/browse" class="cta-button">
                            Explore Our Content
                        </a>
                    </div>
                    
                    <p>If you have any questions or need support, don't hesitate to reach out to us at <a href="mailto:{self.support_email}">{self.support_email}</a>.</p>
                    
                    <p>Here's to your wellness journey!</p>
                    
                    <p><strong>The Better & Bliss Team</strong></p>
                </div>
                
                <div class="footer">
                    <p>Better & Bliss Mental Health & Wellness Platform</p>
                    <p>You're receiving this because you subscribed to our newsletter.</p>
                    <p><a href="{unsubscribe_url}" class="unsubscribe">Unsubscribe</a></p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _create_welcome_email_text(self, name: str, unsubscribe_url: str) -> str:
        """Create plain text content for welcome email"""
        return f"""
Welcome to Better & Bliss!

Hi {name},

Thank you for joining our wellness community! We're thrilled to have you on this journey toward better mental health and personal growth.

What you can expect:
• Weekly wellness tips from licensed mental health professionals
• Practical exercises for stress management and mindfulness  
• Expert insights on anxiety, depression, and emotional wellness
• Early access to new content and features
• Supportive community resources

Our mission is to make mental health resources accessible, practical, and stigma-free. Every email we send is designed to provide you with actionable insights that can make a real difference in your daily life.

Explore our content: {settings.frontend_url}/browse

If you have any questions or need support, don't hesitate to reach out to us at {self.support_email}.

Here's to your wellness journey!

The Better & Bliss Team

---
Better & Bliss Mental Health & Wellness Platform
You're receiving this because you subscribed to our newsletter.
Unsubscribe: {unsubscribe_url}
        """

# Global email service instance
email_service = EmailService()