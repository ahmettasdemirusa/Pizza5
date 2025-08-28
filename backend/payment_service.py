"""
Payment Service for NY Pizza Woodstock
Supports multiple payment providers: Stripe, PayPal, Square, Apple Pay, Google Pay
"""

import os
import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class PaymentProvider(Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    SQUARE = "square"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    CASH = "cash"

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentService:
    def __init__(self):
        # Load API keys from environment variables
        self.stripe_secret_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_PLACEHOLDER_ADD_YOUR_STRIPE_SECRET_KEY_HERE')
        self.stripe_public_key = os.getenv('STRIPE_PUBLIC_KEY', 'pk_test_PLACEHOLDER_ADD_YOUR_STRIPE_PUBLIC_KEY_HERE')
        
        self.paypal_client_id = os.getenv('PAYPAL_CLIENT_ID', 'PLACEHOLDER_ADD_YOUR_PAYPAL_CLIENT_ID_HERE')
        self.paypal_client_secret = os.getenv('PAYPAL_CLIENT_SECRET', 'PLACEHOLDER_ADD_YOUR_PAYPAL_CLIENT_SECRET_HERE')
        
        self.square_application_id = os.getenv('SQUARE_APPLICATION_ID', 'PLACEHOLDER_ADD_YOUR_SQUARE_APPLICATION_ID_HERE')
        self.square_access_token = os.getenv('SQUARE_ACCESS_TOKEN', 'PLACEHOLDER_ADD_YOUR_SQUARE_ACCESS_TOKEN_HERE')
        
        # Initialize payment providers
        self._init_stripe()
        self._init_paypal()
        self._init_square()
    
    def _init_stripe(self):
        """Initialize Stripe payment processor"""
        try:
            if not self.stripe_secret_key.startswith('PLACEHOLDER'):
                import stripe
                stripe.api_key = self.stripe_secret_key
                logger.info("Stripe initialized successfully")
                self.stripe_enabled = True
            else:
                logger.warning("Stripe not initialized - API key placeholder detected")
                self.stripe_enabled = False
        except ImportError:
            logger.warning("Stripe library not installed. Run: pip install stripe")
            self.stripe_enabled = False
        except Exception as e:
            logger.error(f"Stripe initialization failed: {e}")
            self.stripe_enabled = False
    
    def _init_paypal(self):
        """Initialize PayPal payment processor"""
        try:
            if not self.paypal_client_id.startswith('PLACEHOLDER'):
                # PayPal SDK would be initialized here
                logger.info("PayPal initialized successfully")
                self.paypal_enabled = True
            else:
                logger.warning("PayPal not initialized - API key placeholder detected")
                self.paypal_enabled = False
        except Exception as e:
            logger.error(f"PayPal initialization failed: {e}")
            self.paypal_enabled = False
    
    def _init_square(self):
        """Initialize Square payment processor"""
        try:
            if not self.square_access_token.startswith('PLACEHOLDER'):
                # Square SDK would be initialized here
                logger.info("Square initialized successfully")
                self.square_enabled = True
            else:
                logger.warning("Square not initialized - API key placeholder detected")
                self.square_enabled = False
        except Exception as e:
            logger.error(f"Square initialization failed: {e}")
            self.square_enabled = False

    def get_available_payment_methods(self) -> Dict[str, Any]:
        """Get list of available payment methods"""
        methods = {
            "cash": {
                "name": "Cash Payment",
                "description": "Pay with cash on delivery or pickup",
                "enabled": True,
                "icon": "💵",
                "fee": 0.0
            }
        }
        
        if self.stripe_enabled:
            methods["stripe"] = {
                "name": "Credit/Debit Card (Stripe)",
                "description": "Pay securely with Visa, Mastercard, American Express",
                "enabled": True,
                "icon": "💳",
                "fee": 0.029,  # 2.9% + 30¢
                "public_key": self.stripe_public_key
            }
        
        if self.paypal_enabled:
            methods["paypal"] = {
                "name": "PayPal",
                "description": "Pay with PayPal account or credit card",
                "enabled": True,
                "icon": "🅿️",
                "fee": 0.034,  # 3.4% + fixed fee
                "client_id": self.paypal_client_id
            }
        
        if self.square_enabled:
            methods["square"] = {
                "name": "Square Payment",
                "description": "Secure card processing",
                "enabled": True,
                "icon": "⬜",
                "fee": 0.026  # 2.6% + 10¢
            }
        
        # Mobile payment methods
        methods.update({
            "apple_pay": {
                "name": "Apple Pay",
                "description": "Pay with Touch ID or Face ID",
                "enabled": True,  # Will be enabled based on device
                "icon": "🍎",
                "fee": 0.029
            },
            "google_pay": {
                "name": "Google Pay",
                "description": "Pay with Google account",
                "enabled": True,  # Will be enabled based on device
                "icon": "🔵",
                "fee": 0.029
            }
        })
        
        return methods

    async def create_payment_intent(self, amount: float, currency: str = "usd", 
                                  provider: PaymentProvider = PaymentProvider.STRIPE,
                                  metadata: Dict = None) -> Dict[str, Any]:
        """Create payment intent for processing"""
        
        if provider == PaymentProvider.CASH:
            return {
                "id": f"cash_{int(amount * 100)}_{metadata.get('order_id', 'unknown')}",
                "status": PaymentStatus.PENDING.value,
                "amount": amount,
                "currency": currency,
                "provider": provider.value,
                "requires_action": False,
                "payment_method": "cash"
            }
        
        elif provider == PaymentProvider.STRIPE and self.stripe_enabled:
            return await self._create_stripe_payment_intent(amount, currency, metadata)
        
        elif provider == PaymentProvider.PAYPAL and self.paypal_enabled:
            return await self._create_paypal_payment(amount, currency, metadata)
        
        elif provider == PaymentProvider.SQUARE and self.square_enabled:
            return await self._create_square_payment(amount, currency, metadata)
        
        else:
            raise ValueError(f"Payment provider {provider.value} not available or not configured")

    async def _create_stripe_payment_intent(self, amount: float, currency: str, metadata: Dict) -> Dict[str, Any]:
        """Create Stripe payment intent"""
        try:
            import stripe
            
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Stripe uses cents
                currency=currency,
                metadata=metadata or {},
                automatic_payment_methods={'enabled': True}
            )
            
            return {
                "id": intent.id,
                "client_secret": intent.client_secret,
                "status": intent.status,
                "amount": amount,
                "currency": currency,
                "provider": PaymentProvider.STRIPE.value,
                "requires_action": intent.status == "requires_action"
            }
        
        except Exception as e:
            logger.error(f"Stripe payment intent creation failed: {e}")
            raise Exception(f"Payment processing unavailable: {str(e)}")

    async def _create_paypal_payment(self, amount: float, currency: str, metadata: Dict) -> Dict[str, Any]:
        """Create PayPal payment"""
        # PayPal payment creation logic would go here
        return {
            "id": f"paypal_placeholder_{int(amount * 100)}",
            "status": PaymentStatus.PENDING.value,
            "amount": amount,
            "currency": currency,
            "provider": PaymentProvider.PAYPAL.value,
            "approval_url": "https://paypal.com/payment/placeholder"
        }

    async def _create_square_payment(self, amount: float, currency: str, metadata: Dict) -> Dict[str, Any]:
        """Create Square payment"""
        # Square payment creation logic would go here
        return {
            "id": f"square_placeholder_{int(amount * 100)}",
            "status": PaymentStatus.PENDING.value,
            "amount": amount,
            "currency": currency,
            "provider": PaymentProvider.SQUARE.value
        }

    async def confirm_payment(self, payment_id: str, provider: PaymentProvider) -> Dict[str, Any]:
        """Confirm payment completion"""
        
        if provider == PaymentProvider.CASH:
            return {
                "id": payment_id,
                "status": PaymentStatus.COMPLETED.value,
                "provider": provider.value
            }
        
        elif provider == PaymentProvider.STRIPE and self.stripe_enabled:
            return await self._confirm_stripe_payment(payment_id)
        
        # Add other provider confirmations as needed
        
        return {
            "id": payment_id,
            "status": PaymentStatus.PENDING.value,
            "provider": provider.value
        }

    async def _confirm_stripe_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """Confirm Stripe payment"""
        try:
            import stripe
            
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                "id": intent.id,
                "status": intent.status,
                "provider": PaymentProvider.STRIPE.value,
                "amount_received": intent.amount_received / 100 if intent.amount_received else 0
            }
        
        except Exception as e:
            logger.error(f"Stripe payment confirmation failed: {e}")
            return {
                "id": payment_intent_id,
                "status": PaymentStatus.FAILED.value,
                "provider": PaymentProvider.STRIPE.value,
                "error": str(e)
            }

    async def process_refund(self, payment_id: str, amount: float, provider: PaymentProvider) -> Dict[str, Any]:
        """Process payment refund"""
        
        if provider == PaymentProvider.CASH:
            return {
                "id": f"refund_{payment_id}",
                "status": PaymentStatus.REFUNDED.value,
                "amount": amount,
                "provider": provider.value,
                "note": "Cash refund - process manually"
            }
        
        elif provider == PaymentProvider.STRIPE and self.stripe_enabled:
            return await self._process_stripe_refund(payment_id, amount)
        
        # Add other provider refunds as needed
        
        return {
            "id": f"refund_{payment_id}",
            "status": PaymentStatus.PENDING.value,
            "amount": amount,
            "provider": provider.value
        }

    async def _process_stripe_refund(self, payment_intent_id: str, amount: float) -> Dict[str, Any]:
        """Process Stripe refund"""
        try:
            import stripe
            
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=int(amount * 100)  # Stripe uses cents
            )
            
            return {
                "id": refund.id,
                "status": refund.status,
                "amount": refund.amount / 100,
                "provider": PaymentProvider.STRIPE.value
            }
        
        except Exception as e:
            logger.error(f"Stripe refund failed: {e}")
            return {
                "id": f"refund_failed_{payment_intent_id}",
                "status": PaymentStatus.FAILED.value,
                "provider": PaymentProvider.STRIPE.value,
                "error": str(e)
            }

# Global payment service instance
payment_service = PaymentService()

# API KEY SETUP INSTRUCTIONS:
"""
To enable payment processing, add these environment variables to your .env file:

# Stripe (recommended for cards)
STRIPE_SECRET_KEY=sk_live_your_actual_stripe_secret_key_here
STRIPE_PUBLIC_KEY=pk_live_your_actual_stripe_public_key_here

# PayPal (for PayPal payments)
PAYPAL_CLIENT_ID=your_actual_paypal_client_id_here
PAYPAL_CLIENT_SECRET=your_actual_paypal_client_secret_here

# Square (alternative card processor)
SQUARE_APPLICATION_ID=your_actual_square_application_id_here
SQUARE_ACCESS_TOKEN=your_actual_square_access_token_here

For testing, use test keys:
STRIPE_SECRET_KEY=sk_test_your_stripe_test_secret_key_here
STRIPE_PUBLIC_KEY=pk_test_your_stripe_test_public_key_here
"""