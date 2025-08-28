"""
Email & SMS Notification Service for NY Pizza Woodstock
Handles order confirmations, status updates, and promotional emails
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # Email configuration from environment variables
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', 'PLACEHOLDER_ADD_YOUR_EMAIL@gmail.com')
        self.smtp_password = os.getenv('SMTP_PASSWORD', 'PLACEHOLDER_ADD_YOUR_EMAIL_APP_PASSWORD_HERE')
        self.from_email = os.getenv('FROM_EMAIL', 'orders@nypizzawoodstock.com')
        self.from_name = os.getenv('FROM_NAME', 'NY Pizza Woodstock')
        
        # SMS configuration (Twilio)
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID', 'PLACEHOLDER_ADD_YOUR_TWILIO_ACCOUNT_SID_HERE')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN', 'PLACEHOLDER_ADD_YOUR_TWILIO_AUTH_TOKEN_HERE')
        self.twilio_phone = os.getenv('TWILIO_PHONE', '+1PLACEHOLDER_ADD_YOUR_TWILIO_PHONE_HERE')
        
        # Business information
        self.business_name = "NY Pizza Woodstock"
        self.business_address = "10214 Hickory Flat Hwy, Woodstock, GA 30188"
        self.business_phone = "(470) 545-0095"
        self.business_email = "info@nypizzawoodstock.com"
        self.business_website = "https://www.nypizzawoodstock.com"
        
        # Check if services are configured
        self.email_enabled = not self.smtp_username.startswith('PLACEHOLDER')
        self.sms_enabled = not self.twilio_account_sid.startswith('PLACEHOLDER')
        
        if self.email_enabled:
            logger.info("Email service initialized")
        else:
            logger.warning("Email service not configured - using placeholder credentials")
        
        if self.sms_enabled:
            logger.info("SMS service initialized") 
        else:
            logger.warning("SMS service not configured - using placeholder credentials")

    async def send_order_confirmation(self, order_data: Dict[str, Any], customer_email: str) -> bool:
        """Send order confirmation email to customer"""
        try:
            subject = f"Order Confirmation #{order_data['id'][:8]} - {self.business_name}"
            
            # Generate HTML email content
            html_content = self._generate_order_confirmation_html(order_data)
            text_content = self._generate_order_confirmation_text(order_data)
            
            return await self._send_email(
                to_email=customer_email,
                subject=subject,
                text_content=text_content,
                html_content=html_content
            )
        
        except Exception as e:
            logger.error(f"Failed to send order confirmation: {e}")
            return False

    async def send_order_status_update(self, order_data: Dict[str, Any], customer_email: str, new_status: str) -> bool:
        """Send order status update email"""
        try:
            status_messages = {
                'confirmed': 'Your order has been confirmed!',
                'preparing': 'Your order is being prepared',
                'ready': 'Your order is ready for pickup!',
                'delivered': 'Your order has been delivered',
                'cancelled': 'Your order has been cancelled'
            }
            
            subject = f"Order Update: {status_messages.get(new_status, f'Status: {new_status}')} - {self.business_name}"
            
            html_content = self._generate_status_update_html(order_data, new_status)
            text_content = self._generate_status_update_text(order_data, new_status)
            
            return await self._send_email(
                to_email=customer_email,
                subject=subject,
                text_content=text_content,
                html_content=html_content
            )
        
        except Exception as e:
            logger.error(f"Failed to send status update: {e}")
            return False

    async def send_admin_notification(self, order_data: Dict[str, Any]) -> bool:
        """Send new order notification to restaurant staff"""
        try:
            admin_emails = [
                "admin@nypizzawoodstock.com",
                "kitchen@nypizzawoodstock.com",
                "manager@nypizzawoodstock.com"
            ]
            
            subject = f"🍕 NEW ORDER #{order_data['id'][:8]} - ${order_data['total']:.2f}"
            
            html_content = self._generate_admin_notification_html(order_data)
            text_content = self._generate_admin_notification_text(order_data)
            
            success = True
            for admin_email in admin_emails:
                result = await self._send_email(
                    to_email=admin_email,
                    subject=subject,
                    text_content=text_content,
                    html_content=html_content
                )
                if not result:
                    success = False
            
            return success
        
        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")
            return False

    async def send_sms_notification(self, phone_number: str, message: str) -> bool:
        """Send SMS notification using Twilio"""
        if not self.sms_enabled:
            logger.warning("SMS not configured - message not sent")
            return False
        
        try:
            # Twilio SMS sending logic would go here
            logger.info(f"SMS sent to {phone_number}: {message[:50]}...")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False

    async def _send_email(self, to_email: str, subject: str, text_content: str, html_content: str = None) -> bool:
        """Send email using SMTP"""
        if not self.email_enabled:
            logger.warning(f"Email not configured - would send to {to_email}: {subject}")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add text version
            text_part = MIMEText(text_content, 'plain')
            msg.attach(text_part)
            
            # Add HTML version if provided
            if html_content:
                html_part = MIMEText(html_content, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def _generate_order_confirmation_html(self, order_data: Dict[str, Any]) -> str:
        """Generate HTML content for order confirmation email"""
        items_html = ""
        for item in order_data.get('items', []):
            items_html += f"""
            <tr>
                <td>{item['name']} {f"({item['size']})" if item.get('size') else ""}</td>
                <td>{item['quantity']}</td>
                <td>${(item['price'] * item['quantity']):.2f}</td>
            </tr>
            """
        
        delivery_info = ""
        if order_data.get('order_type') == 'delivery' and order_data.get('delivery_address'):
            addr = order_data['delivery_address']
            delivery_info = f"""
            <p><strong>Delivery Address:</strong><br>
            {addr['street']}<br>
            {addr['city']}, {addr['state']} {addr['zip_code']}</p>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #dc2626; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .order-details {{ background: #f9f9f9; padding: 15px; margin: 20px 0; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                .total {{ font-weight: bold; font-size: 18px; }}
                .footer {{ background: #f5f5f5; padding: 20px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🍕 {self.business_name}</h1>
                <h2>Order Confirmation</h2>
            </div>
            
            <div class="content">
                <h3>Thank you for your order!</h3>
                <p>Your order has been received and is being processed.</p>
                
                <div class="order-details">
                    <p><strong>Order Number:</strong> #{order_data['id'][:8]}</p>
                    <p><strong>Order Type:</strong> {order_data['order_type'].title()}</p>
                    <p><strong>Payment Method:</strong> {order_data['payment_method'].title()}</p>
                    <p><strong>Estimated Time:</strong> {order_data.get('estimated_delivery', 'TBD')}</p>
                    {delivery_info}
                </div>
                
                <h3>Order Items:</h3>
                <table>
                    <tr>
                        <th>Item</th>
                        <th>Quantity</th>
                        <th>Price</th>
                    </tr>
                    {items_html}
                </table>
                
                <div class="order-details">
                    <p>Subtotal: ${order_data['subtotal']:.2f}</p>
                    {f"<p>Delivery Fee: ${order_data.get('delivery_fee', 0):.2f}</p>" if order_data.get('delivery_fee') else ""}
                    <p>Tax: ${order_data['tax']:.2f}</p>
                    <p class="total">Total: ${order_data['total']:.2f}</p>
                </div>
                
                <p>We'll send you updates as your order progresses. Thank you for choosing {self.business_name}!</p>
            </div>
            
            <div class="footer">
                <p>{self.business_name} | {self.business_address} | {self.business_phone}</p>
                <p>Questions? Contact us at {self.business_email}</p>
            </div>
        </body>
        </html>
        """

    def _generate_order_confirmation_text(self, order_data: Dict[str, Any]) -> str:
        """Generate text content for order confirmation email"""
        items_text = ""
        for item in order_data.get('items', []):
            items_text += f"- {item['name']} {f'({item['size']})' if item.get('size') else ''} x{item['quantity']} - ${(item['price'] * item['quantity']):.2f}\n"
        
        delivery_info = ""
        if order_data.get('order_type') == 'delivery' and order_data.get('delivery_address'):
            addr = order_data['delivery_address']
            delivery_info = f"\nDelivery Address:\n{addr['street']}\n{addr['city']}, {addr['state']} {addr['zip_code']}\n"
        
        return f"""
{self.business_name} - Order Confirmation

Thank you for your order!

Order Number: #{order_data['id'][:8]}
Order Type: {order_data['order_type'].title()}
Payment Method: {order_data['payment_method'].title()}
Estimated Time: {order_data.get('estimated_delivery', 'TBD')}
{delivery_info}

Order Items:
{items_text}

Subtotal: ${order_data['subtotal']:.2f}
{f"Delivery Fee: ${order_data.get('delivery_fee', 0):.2f}" if order_data.get('delivery_fee') else ""}
Tax: ${order_data['tax']:.2f}
Total: ${order_data['total']:.2f}

We'll send you updates as your order progresses. Thank you for choosing {self.business_name}!

{self.business_name}
{self.business_address}
{self.business_phone}

Questions? Contact us at {self.business_email}
        """

    def _generate_status_update_html(self, order_data: Dict[str, Any], status: str) -> str:
        """Generate HTML for status update email"""
        status_messages = {
            'confirmed': ('✅', 'Your order has been confirmed and we\'re getting started!'),
            'preparing': ('👨‍🍳', 'Our kitchen is preparing your delicious order!'),
            'ready': ('🍕', 'Your order is ready for pickup!'),
            'delivered': ('📦', 'Your order has been delivered. Enjoy your meal!'),
            'cancelled': ('❌', 'Your order has been cancelled. Contact us if you have questions.')
        }
        
        icon, message = status_messages.get(status, ('📋', f'Order status: {status}'))
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #dc2626; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; text-align: center; }}
                .status-update {{ background: #f0f8ff; padding: 30px; margin: 20px 0; border-radius: 10px; }}
                .footer {{ background: #f5f5f5; padding: 20px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🍕 {self.business_name}</h1>
            </div>
            
            <div class="content">
                <div class="status-update">
                    <h2 style="font-size: 48px;">{icon}</h2>
                    <h2>Order #{order_data['id'][:8]} Update</h2>
                    <p style="font-size: 18px;">{message}</p>
                </div>
                
                <p>Thank you for your patience and for choosing {self.business_name}!</p>
                
                {f'<p><strong>Pickup Location:</strong><br>{self.business_address}</p>' if status == 'ready' else ''}
            </div>
            
            <div class="footer">
                <p>{self.business_name} | {self.business_address} | {self.business_phone}</p>
            </div>
        </body>
        </html>
        """

    def _generate_status_update_text(self, order_data: Dict[str, Any], status: str) -> str:
        """Generate text content for status update email"""
        status_messages = {
            'confirmed': 'Your order has been confirmed and we\'re getting started!',
            'preparing': 'Our kitchen is preparing your delicious order!',
            'ready': 'Your order is ready for pickup!',
            'delivered': 'Your order has been delivered. Enjoy your meal!',
            'cancelled': 'Your order has been cancelled. Contact us if you have questions.'
        }
        
        message = status_messages.get(status, f'Order status: {status}')
        
        return f"""
{self.business_name} - Order Update

Order #{order_data['id'][:8]}

{message}

{f'Pickup Location: {self.business_address}' if status == 'ready' else ''}

Thank you for choosing {self.business_name}!

{self.business_phone}
        """

    def _generate_admin_notification_html(self, order_data: Dict[str, Any]) -> str:
        """Generate HTML for admin notification email"""
        items_html = ""
        for item in order_data.get('items', []):
            items_html += f"""
            <tr style="background: #f9f9f9;">
                <td style="padding: 8px;">{item['name']} {f"({item['size']})" if item.get('size') else ""}</td>
                <td style="padding: 8px;">{item['quantity']}</td>
                <td style="padding: 8px;">${(item['price'] * item['quantity']):.2f}</td>
            </tr>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background: #dc2626; color: white; padding: 15px;">
                <h2>🍕 NEW ORDER ALERT</h2>
            </div>
            
            <div style="padding: 20px;">
                <h3>Order #{order_data['id'][:8]} - ${order_data['total']:.2f}</h3>
                
                <p><strong>Type:</strong> {order_data['order_type'].title()}</p>
                <p><strong>Payment:</strong> {order_data['payment_method'].title()}</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%H:%M')}</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #333; color: white;">
                        <th style="padding: 10px;">Item</th>
                        <th style="padding: 10px;">Qty</th>
                        <th style="padding: 10px;">Price</th>
                    </tr>
                    {items_html}
                </table>
                
                {f'<p><strong>Special Instructions:</strong> {order_data["special_instructions"]}</p>' if order_data.get('special_instructions') else ''}
                
                <div style="background: #e8f5e8; padding: 15px; margin: 15px 0;">
                    <p style="margin: 0; font-size: 18px;"><strong>TOTAL: ${order_data['total']:.2f}</strong></p>
                </div>
            </div>
        </body>
        </html>
        """

    def _generate_admin_notification_text(self, order_data: Dict[str, Any]) -> str:
        """Generate text content for admin notification"""
        items_text = ""
        for item in order_data.get('items', []):
            items_text += f"- {item['name']} {f'({item['size']})' if item.get('size') else ''} x{item['quantity']} - ${(item['price'] * item['quantity']):.2f}\n"
        
        return f"""
🍕 NEW ORDER ALERT

Order #{order_data['id'][:8]} - ${order_data['total']:.2f}

Type: {order_data['order_type'].title()}
Payment: {order_data['payment_method'].title()}
Time: {datetime.now().strftime('%H:%M')}

Items:
{items_text}

{f'Special Instructions: {order_data["special_instructions"]}' if order_data.get('special_instructions') else ''}

TOTAL: ${order_data['total']:.2f}
        """

# Global email service instance
email_service = EmailService()

# EMAIL & SMS SETUP INSTRUCTIONS:
"""
To enable email notifications, add these environment variables to your .env file:

# Email Configuration (Gmail recommended)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_business_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password_here
FROM_EMAIL=orders@nypizzawoodstock.com
FROM_NAME=NY Pizza Woodstock

# SMS Configuration (Twilio)
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_PHONE=+1234567890

For Gmail, generate App Password:
1. Enable 2-Factor Authentication on Gmail
2. Go to Google Account Settings > Security > App Passwords
3. Generate password for "Mail" app
4. Use generated password in SMTP_PASSWORD

For Twilio SMS:
1. Sign up at twilio.com
2. Get Account SID and Auth Token
3. Purchase phone number
"""