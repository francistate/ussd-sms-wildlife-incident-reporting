"""
Africa's Talking SMS Service
Handles sending and receiving SMS via Africa's Talking API
"""
import africastalking
import logging
from typing import List, Optional, Dict, Any

from config import settings

logger = logging.getLogger(__name__)


class SMSService:
    """Africa's Talking SMS Service wrapper"""

    def __init__(self):
        """Initialize Africa's Talking SDK"""
        self.username = settings.at_username
        self.api_key = settings.at_api_key
        self.shortcode = settings.at_shortcode

        if not self.username or not self.api_key:
            raise ValueError("AT_USERNAME and AT_API_KEY must be set")

        # Initialize Africa's Talking
        africastalking.initialize(self.username, self.api_key)

        # Get SMS service
        self.sms = africastalking.SMS

        logger.info(f"SMS Service initialized with username: {self.username}")

    def send_sms(
        self,
        message: str,
        recipients: List[str],
        sender_id: Optional[str] = None,
        enqueue: bool = True,
        log_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Send SMS to one or more recipients

        Args:
            message: SMS message text
            recipients: List of phone numbers in international format (+254...)
            sender_id: Optional sender ID (alphanumeric or shortcode)
            enqueue: Whether to queue messages (True) or send immediately
            log_to_db: Whether to log outgoing messages to database

        Returns:
            Dictionary with response from Africa's Talking API
            Includes message_ids for delivery tracking
        """
        try:
            # Use shortcode as sender if no sender_id provided
            if sender_id is None:
                sender_id = self.shortcode

            # Send SMS
            response = self.sms.send(
                message=message,
                recipients=recipients,
                sender_id=sender_id,
                enqueue=enqueue
            )

            logger.info(f"SMS sent to {len(recipients)} recipient(s)")
            logger.debug(f"Response: {response}")

            # Extract message IDs from response for delivery tracking
            # Response format: {'SMSMessageData': {'Message': '...', 'Recipients': [{'number': '+254...', 'messageId': '...', 'status': '...'}]}}
            message_ids = []
            sms_data = response.get('SMSMessageData', {})
            for recipient in sms_data.get('Recipients', []):
                msg_id = recipient.get('messageId')
                phone = recipient.get('number')
                status = recipient.get('status')
                if msg_id:
                    message_ids.append({
                        'message_id': msg_id,
                        'phone_number': phone,
                        'status': status
                    })

                    # Log to database if enabled
                    if log_to_db:
                        self._log_outgoing(msg_id, phone, message, status)

            return {
                "success": True,
                "response": response,
                "message_ids": message_ids
            }

        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _log_outgoing(self, message_id: str, phone_number: str, message_text: str, status: str):
        """Log outgoing message to database for delivery tracking"""
        try:
            from database.connection import get_db
            from database.repository import SMSMessageRepository

            with get_db() as db:
                repo = SMSMessageRepository(db)
                repo.log_outgoing(
                    message_id=message_id,
                    phone_number=phone_number,
                    message_text=message_text
                )
                # Update initial status
                from database.models import SMSMessage
                msg = db.query(SMSMessage).filter(SMSMessage.message_id == message_id).first()
                if msg:
                    msg.status = status.lower() if status else 'sent'
                db.commit()
        except Exception as e:
            logger.warning(f"Failed to log outgoing message: {e}")

    def send_single(
        self,
        message: str,
        phone_number: str,
        sender_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send SMS to single recipient"""
        return self.send_sms(message, [phone_number], sender_id)

    def fetch_messages(self, last_received_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch incoming SMS messages from Africa's Talking API

        Args:
            last_received_id: ID of last message received (for pagination)

        Returns:
            Dictionary with messages
        """
        try:
            response = self.sms.fetch_messages(last_received_id=last_received_id or 0)
            logger.info("Fetched messages from API")
            return {
                "success": True,
                "messages": response
            }
        except Exception as e:
            logger.error(f"Failed to fetch messages: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global SMS service instance
_sms_service: Optional[SMSService] = None


def init_sms_service() -> SMSService:
    """Initialize the global SMS service instance"""
    global _sms_service
    try:
        _sms_service = SMSService()
        return _sms_service
    except Exception as e:
        logger.error(f"Failed to initialize SMS service: {e}")
        raise


def get_sms_service() -> Optional[SMSService]:
    """Get the global SMS service instance"""
    return _sms_service
