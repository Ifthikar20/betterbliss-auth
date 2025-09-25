# enhanced_ses_test.py - Complete SES test with welcome email template
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv
from datetime import datetime
import uuid

load_dotenv()

def create_welcome_email_html(name, unsubscribe_url):
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
                
                <p>Thank you for joining our mental wellness community. Taking the first step toward better mental health is both brave and important, and we're honored to be part of your journey.</p>
                
                <div class="highlight-box">
                    <h3>What you can expect from Better & Bliss:</h3>
                    <ul class="benefits">
                        <li>Evidence-based wellness strategies from licensed mental health professionals</li>
                        <li>Practical tools for managing stress, anxiety, and emotional well-being</li>
                        <li>Mindfulness techniques and self-care practices you can use daily</li>
                        <li>Resources for building resilience and emotional intelligence</li>
                        <li>A supportive, judgment-free approach to mental health</li>
                    </ul>
                </div>
                
                <p>Mental health is health. Our content is designed to complement professional care and provide you with accessible, actionable insights that can make a meaningful difference in your daily life.</p>
                
                <p><strong>Important:</strong> If you're experiencing a mental health crisis, please reach out to a qualified professional, your doctor, or a crisis helpline. Our content is educational and supportive, but not a substitute for professional mental health care.</p>
                
                <div style="text-align: center;">
                    <a href="{os.getenv('FRONTEND_URL', 'https://betterandbliss.com')}/resources" class="cta-button">
                        Explore Wellness Resources
                    </a>
                </div>
                
                <p>We're here to support you. If you have questions, please reach out to us at {os.getenv('SUPPORT_EMAIL', 'support@betterandbliss.com')}.</p>
                
                <p>Take care of yourself,</p>
                <p><strong>The Better & Bliss Team</strong></p>
            </div>
            
            <div class="footer">
                <p><strong>Better & Bliss</strong> - Mental Health & Wellness Platform</p>
                <p>Committed to making mental health resources accessible and stigma-free</p>
                <p style="margin-top: 15px;">
                    <strong>Crisis Resources:</strong><br>
                    National Suicide Prevention Lifeline: 988<br>
                    Crisis Text Line: Text HOME to 741741
                </p>
                <p style="margin-top: 15px;">
                    You're receiving this because you subscribed to our newsletter.<br>
                    <a href="{unsubscribe_url}" class="unsubscribe">Unsubscribe at any time</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """

def create_welcome_email_text(name, unsubscribe_url):
    """Create plain text content for welcome email"""
    return f"""
Welcome to Better & Bliss!

Hi {name},

Thank you for joining our mental wellness community. Taking the first step toward better mental health is both brave and important, and we're honored to be part of your journey.

What you can expect from Better & Bliss:
• Evidence-based wellness strategies from licensed mental health professionals
• Practical tools for managing stress, anxiety, and emotional well-being
• Mindfulness techniques and self-care practices you can use daily
• Resources for building resilience and emotional intelligence
• A supportive, judgment-free approach to mental health

Mental health is health. Our content is designed to complement professional care and provide you with accessible, actionable insights that can make a meaningful difference in your daily life.

IMPORTANT: If you're experiencing a mental health crisis, please reach out to a qualified professional, your doctor, or a crisis helpline. Our content is educational and supportive, but not a substitute for professional mental health care.

Explore our wellness resources: {os.getenv('FRONTEND_URL', 'https://betterandbliss.com')}/resources

We're here to support you. If you have questions, please reach out to us at {os.getenv('SUPPORT_EMAIL', 'support@betterandbliss.com')}.

Take care of yourself,

The Better & Bliss Team

---
Better & Bliss - Mental Health & Wellness Platform
Committed to making mental health resources accessible and stigma-free

Crisis Resources:
National Suicide Prevention Lifeline: 988
Crisis Text Line: Text HOME to 741741

You're receiving this because you subscribed to our newsletter.
Unsubscribe at any time: {unsubscribe_url}
    """

def test_simple_email(ses_client, from_email, to_email):
    """Test with simple plain text email"""
    print("\n" + "="*50)
    print("TESTING SIMPLE EMAIL")
    print("="*50)
    
    try:
        response = ses_client.send_email(
            FromEmailAddress=from_email,
            Destination={'ToAddresses': [to_email]},
            Content={
                'Simple': {
                    'Subject': {'Data': 'SES Test Email', 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': 'This is a simple test email from SES', 'Charset': 'UTF-8'}
                    }
                }
            }
        )
        print(f"✅ SUCCESS! Message ID: {response['MessageId']}")
        return True
    except ClientError as e:
        print(f"❌ ERROR: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False

def test_welcome_email(ses_client, from_email, to_email):
    """Test with full welcome email template"""
    print("\n" + "="*50)
    print("TESTING WELCOME EMAIL")
    print("="*50)
    
    # Generate test data
    name = input("Enter recipient name (or press Enter for 'Friend'): ").strip() or "Friend"
    subscription_id = str(uuid.uuid4())
    unsubscribe_url = f"{os.getenv('FRONTEND_URL', 'https://betterandbliss.com')}/unsubscribe?id={subscription_id}"
    
    print(f"📧 Recipient: {name}")
    print(f"🔗 Unsubscribe URL: {unsubscribe_url}")
    
    # Create email content
    subject = "Welcome to Better & Bliss - Your Mental Wellness Journey Starts Here"
    html_content = create_welcome_email_html(name, unsubscribe_url)
    text_content = create_welcome_email_text(name, unsubscribe_url)
    
    print(f"📝 Subject: {subject}")
    print(f"📄 HTML length: {len(html_content)} chars")
    print(f"📄 Text length: {len(text_content)} chars")
    
    try:
        email_params = {
            'FromEmailAddress': f"Better & Bliss <{from_email}>",
            'Destination': {'ToAddresses': [to_email]},
            'Content': {
                'Simple': {
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': html_content, 'Charset': 'UTF-8'},
                        'Text': {'Data': text_content, 'Charset': 'UTF-8'}
                    }
                }
            },
            'ReplyToAddresses': [os.getenv('SUPPORT_EMAIL', from_email)]
        }
        
        print("🚀 Sending welcome email...")
        response = ses_client.send_email(**email_params)
        
        print(f"✅ SUCCESS! Welcome email sent!")
        print(f"📨 Message ID: {response['MessageId']}")
        print(f"⏰ Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
        
    except ClientError as e:
        print(f"❌ SES ERROR: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False

def main():
    print("🌟 ENHANCED SES TESTING TOOL")
    print("=" * 50)
    
    # Initialize SES client
    region = os.getenv('AWS_REGION', 'us-east-1')
    ses_client = boto3.client('sesv2', region_name=region)
    
    from_email = os.getenv('FROM_EMAIL')
    support_email = os.getenv('SUPPORT_EMAIL')
    frontend_url = os.getenv('FRONTEND_URL')
    
    print(f"📤 FROM_EMAIL: {from_email}")
    print(f"📧 SUPPORT_EMAIL: {support_email}")
    print(f"🌐 FRONTEND_URL: {frontend_url}")
    print(f"🌍 AWS_REGION: {region}")
    
    if not from_email:
        print("❌ ERROR: FROM_EMAIL not set in environment variables")
        return
    
    to_email = input("\nEnter recipient email address: ").strip()
    if not to_email:
        print("❌ ERROR: No recipient email provided")
        return
    
    print(f"📬 TO_EMAIL: {to_email}")
    
    # Test menu
    while True:
        print("\n" + "="*50)
        print("SELECT TEST TYPE:")
        print("1. Simple text email (basic test)")
        print("2. Full welcome email (HTML + text)")
        print("3. Both tests")
        print("4. Exit")
        print("="*50)
        
        choice = input("Enter choice (1-4): ").strip()
        
        if choice == '1':
            test_simple_email(ses_client, from_email, to_email)
        elif choice == '2':
            test_welcome_email(ses_client, from_email, to_email)
        elif choice == '3':
            test_simple_email(ses_client, from_email, to_email)
            test_welcome_email(ses_client, from_email, to_email)
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-4.")
        
        # Ask if user wants to continue
        if choice in ['1', '2', '3']:
            continue_test = input("\nTest another email? (y/n): ").strip().lower()
            if continue_test != 'y':
                print("👋 Testing complete!")
                break

if __name__ == "__main__":
    main()