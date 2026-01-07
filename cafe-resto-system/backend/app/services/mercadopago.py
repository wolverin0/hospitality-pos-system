"""
Mercado Pago QR Payment Service
Handles integration with Mercado Pago API for QR code payments
"""

import os
import logging
import qrcode
from io import BytesIO
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

try:
    import mercadopago
    from mercadopago.config import RequestOptions
    MERCADOPAGO_AVAILABLE = True
except ImportError:
    MERCADOPAGO_AVAILABLE = False
    mercadopago = None
    RequestOptions = None

logger = logging.getLogger(__name__)


class MercadoPagoService:
    """Mercado Pago QR payment service"""

    def __init__(self, access_token: Optional[str] = None, use_sandbox: bool = True):
        """
        Initialize Mercado Pago service

        Args:
            access_token: Mercado Pago access token (defaults to env var)
            use_sandbox: Use sandbox environment (default: True)
        """
        self.access_token = access_token or os.getenv("MERCADOPAGO_ACCESS_TOKEN")
        self.use_sandbox = use_sandbox

        if not self.access_token:
            raise ValueError("MERCADOPAGO_ACCESS_TOKEN is required")

        if MERCADOPAGO_AVAILABLE:
            # Initialize SDK
            self.sdk = mercadopago.SDK(self.access_token)
        else:
            logger.warning("mercadopago SDK not installed, using mock mode")
            self.sdk = None

    def create_qr_order(
        self,
        table_id: str,
        order_id: str,
        total_amount: Decimal,
        items: list,
        external_reference: str,
        expiration_minutes: int = 30,
        tip_amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Create a QR code order with Mercado Pago

        Args:
            table_id: Table identifier (e.g., "TABLE_5")
            order_id: Internal order UUID
            total_amount: Total payment amount
            items: List of order items with titles, quantities, unit prices
            external_reference: Unique reference for idempotency
            expiration_minutes: QR code expiration time (default: 30)
            tip_amount: Optional tip amount

        Returns:
            Dict with order_id, qr_data, qr_image_path, status
        """
        # Include tip in total if provided
        payment_amount = total_amount + (tip_amount or Decimal("0.00"))

        order_data = {
            "type": "qr",
            "total_amount": str(payment_amount),
            "description": f"Table {table_id} - Order {order_id}",
            "external_reference": external_reference,
            "expiration_time": f"PT{expiration_minutes}M",
            "config": {
                "qr": {
                    "external_pos_id": table_id,
                    "mode": "static"  # Static QR for table reuse
                }
            },
            "items": self._format_items(items)
        }

        # Add idempotency header
        request_options = None
        if RequestOptions and self.sdk:
            request_options = RequestOptions()
            request_options.custom_headers = {
                'x-idempotency-key': f"{external_reference}_{datetime.now().isoformat()}"
            }

        try:
            if self.sdk:
                # Real Mercado Pago API call
                result = self.sdk.order().create(order_data, request_options)

                if result.get("status") == 201:
                    order = result["response"]
                    qr_data = order["type_response"]["qr_data"]

                    # Generate QR code image
                    qr_path = self._generate_qr_image(
                        qr_data,
                        table_id,
                        order_id
                    )

                    # Calculate expiration time
                    expires_at = datetime.utcnow() + timedelta(minutes=expiration_minutes)

                    return {
                        "order_id": order["id"],
                        "external_reference": external_reference,
                        "status": order["status"],
                        "qr_data": qr_data,
                        "qr_path": qr_path,
                        "expires_at": expires_at,
                        "total_amount": str(payment_amount)
                    }
                else:
                    error = result.get("response", {})
                    logger.error(f"Mercado Pago order creation failed: {error}")
                    raise Exception(f"Order creation failed: {error}")
            else:
                # Mock mode for testing
                logger.info(f"Mock Mercado Pago order for table {table_id}")
                mock_qr_data = self._generate_mock_qr_data(external_reference)

                qr_path = self._generate_qr_image(
                    mock_qr_data,
                    table_id,
                    order_id
                )

                expires_at = datetime.utcnow() + timedelta(minutes=expiration_minutes)

                return {
                    "order_id": f"MOCK_{order_id}",
                    "external_reference": external_reference,
                    "status": "created",
                    "qr_data": mock_qr_data,
                    "qr_path": qr_path,
                    "expires_at": expires_at,
                    "total_amount": str(payment_amount),
                    "mock": True
                }

        except Exception as e:
            logger.error(f"Error creating Mercado Pago order: {e}")
            raise

    def get_order_status(self, mp_order_id: str) -> Dict[str, Any]:
        """
        Get order status from Mercado Pago

        Args:
            mp_order_id: Mercado Pago order ID

        Returns:
            Dict with status and details
        """
        try:
            if self.sdk:
                result = self.sdk.order().get(mp_order_id)
                return result["response"]
            else:
                # Mock response
                return {
                    "id": mp_order_id,
                    "status": "paid",
                    "external_reference": mp_order_id.replace("MOCK_", "")
                }

        except Exception as e:
            logger.error(f"Error getting Mercado Pago order status: {e}")
            raise

    def verify_webhook_notification(
        self,
        notification: Dict[str, Any]
    ) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Verify webhook notification (no signature verification for QR codes)

        Args:
            notification: Webhook notification payload

        Returns:
            (is_valid, error_message, parsed_data)
        """
        try:
            action_type = notification.get("action_type")

            if action_type != "merchant_orders":
                return False, "Invalid action type", None

            data = notification.get("data", {})
            external_reference = data.get("external_reference")

            if not external_reference:
                return False, "Missing external_reference", None

            # Validate with Mercado Pago API (since signature not available for QR)
            if self.sdk and not data.get("mock"):
                try:
                    mp_order_id = data.get("id")
                    status_result = self.get_order_status(mp_order_id)

                    # Verify external reference matches
                    if status_result.get("external_reference") != external_reference:
                        logger.warning(f"External reference mismatch: {external_reference}")
                        return False, "External reference mismatch", None

                    # Verify status is consistent
                    if status_result.get("status") != data.get("status"):
                        logger.warning(f"Status mismatch: webhook={data.get('status')}, api={status_result.get('status')}")

                except Exception as e:
                    logger.error(f"Error verifying webhook with API: {e}")
                    return False, "Verification failed", None

            return True, "", data

        except Exception as e:
            logger.error(f"Error verifying webhook: {e}")
            return False, str(e), None

    def _format_items(self, items: list) -> list:
        """Format order items for Mercado Pago API"""
        formatted = []

        for item in items:
            formatted_item = {
                "title": item.get("name", "Unknown"),
                "unit_price": str(item.get("unit_price", "0.00")),
                "quantity": item.get("quantity", 1),
                "unit_measure": "unit",
                "external_code": item.get("id", "")
            }
            formatted.append(formatted_item)

        return formatted

    def _generate_qr_image(
        self,
        qr_data: str,
        table_id: str,
        order_id: str
    ) -> str:
        """
        Generate QR code image from EMVCo data

        Args:
            qr_data: EMVCo QR data string
            table_id: Table identifier
            order_id: Order ID

        Returns:
            Path to generated QR image
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Create directory if not exists
            import os
            qr_dir = "static/qrcodes"
            os.makedirs(qr_dir, exist_ok=True)

            filename = f"qr_table_{table_id}_order_{order_id}.png"
            path = os.path.join(qr_dir, filename)
            img.save(path)

            logger.info(f"Generated QR code: {path}")
            return path

        except Exception as e:
            logger.error(f"Error generating QR image: {e}")
            raise

    def _generate_mock_qr_data(self, external_reference: str) -> str:
        """Generate mock QR data for testing"""
        # Simulate EMVCo format (simplified)
        mock_data = (
            "00020101021243650016"
            "COM.MERCADOLIBRE02013063638f1192a"
            f"{external_reference}"
        )
        return mock_data
