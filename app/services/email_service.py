"""
Email service for sending emails via Brevo API.

This module handles all email sending functionality including:
- Brevo API integration
- Template rendering with parameter substitution
- Email logging to database
"""

import os
import re
from datetime import datetime
from flask import current_app, render_template, url_for
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from app import db
from app.models import EmailLog


class EmailService:
    """Service for sending emails via Brevo."""

    def __init__(self, app=None):
        self.app = app
        self._api_instance = None

    def init_app(self, app):
        """Initialize with Flask app."""
        self.app = app

    @property
    def api_instance(self):
        """Get or create Brevo API instance."""
        if self._api_instance is None:
            api_key = os.environ.get('BREVO_API_KEY')
            if not api_key:
                raise ValueError("BREVO_API_KEY environment variable not set")

            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = api_key
            self._api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )
        return self._api_instance

    def _substitute_params(self, html_content: str, params: dict) -> str:
        """Replace {{ params.X }} placeholders with actual values."""
        for key, value in params.items():
            pattern = r'\{\{\s*params\.' + key + r'\s*\}\}'
            html_content = re.sub(pattern, str(value), html_content)
        return html_content

    def _read_template(self, template_file: str) -> str:
        """Read an email template file."""
        template_path = os.path.join(
            current_app.root_path, 'templates', template_file
        )
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _get_image_urls(self) -> dict:
        """Get URLs for email images."""
        app_url = os.environ.get('APP_URL', 'http://localhost:5000')
        return {
            'AI_GUY_LOGO_URL': f"{app_url}/static/emails/Ai_guy_transparent.png",
            'HEADER_IMAGE_URL': f"{app_url}/static/emails/announcment_header.jpg",
            'LOCATION_BG_IMAGE_URL': f"{app_url}/static/emails/announcment_Location_backgound.jpg",
            'INTEL_BG_IMAGE_URL': f"{app_url}/static/emails/announcement_intel_report_background.jpg",
        }

    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        template_file: str,
        params: dict,
        email_type: str,
        lunch_id: int = None,
        dry_run: bool = False
    ) -> dict:
        """
        Send an email via Brevo.

        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject
            template_file: Path to template file (e.g., 'emails/host_confirmation.html')
            params: Dictionary of template parameters
            email_type: Type for logging (host_confirmation, announcement, etc.)
            lunch_id: Optional lunch ID to link in logs
            dry_run: If True, don't actually send (for testing)

        Returns:
            dict with 'success', 'message_id', and 'error' keys
        """
        # Add image URLs to params
        params.update(self._get_image_urls())

        # Read and process template
        raw_html = self._read_template(template_file)
        html_content = self._substitute_params(raw_html, params)

        result = {
            'success': False,
            'message_id': None,
            'error': None
        }

        # Create email log entry
        email_log = EmailLog(
            email_type=email_type,
            recipient_email=to_email,
            recipient_name=to_name,
            subject=subject,
            lunch_id=lunch_id,
            status='pending'
        )
        db.session.add(email_log)

        if dry_run:
            email_log.status = 'dry_run'
            email_log.error_message = 'Dry run - email not sent'
            db.session.commit()
            result['success'] = True
            result['message_id'] = 'dry_run'
            return result

        try:
            # Build Brevo email
            sender = {"name": "Tuesday Lunch Scheduler", "email": "noreply@theaiguy.rocks"}
            to = [{"email": to_email, "name": to_name}]

            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                sender=sender,
                to=to,
                subject=subject,
                html_content=html_content
            )

            # Send via Brevo
            api_response = self.api_instance.send_transac_email(send_smtp_email)

            # Update log with success
            email_log.brevo_message_id = api_response.message_id
            email_log.status = 'sent'
            db.session.commit()

            result['success'] = True
            result['message_id'] = api_response.message_id

        except ApiException as e:
            # Log the error
            email_log.status = 'failed'
            email_log.error_message = str(e)
            db.session.commit()

            result['error'] = str(e)
            current_app.logger.error(f"Brevo API error: {e}")

        except Exception as e:
            email_log.status = 'failed'
            email_log.error_message = str(e)
            db.session.commit()

            result['error'] = str(e)
            current_app.logger.error(f"Email send error: {e}")

        return result

    def send_bulk_email(
        self,
        recipients: list,
        subject: str,
        template_file: str,
        params: dict,
        email_type: str,
        lunch_id: int = None,
        dry_run: bool = False
    ) -> dict:
        """
        Send the same email to multiple recipients.

        Args:
            recipients: List of dicts with 'email' and 'name' keys
            subject: Email subject
            template_file: Path to template file
            params: Dictionary of template parameters (same for all)
            email_type: Type for logging
            lunch_id: Optional lunch ID
            dry_run: If True, don't actually send

        Returns:
            dict with 'sent', 'failed', and 'errors' keys
        """
        results = {
            'sent': 0,
            'failed': 0,
            'errors': []
        }

        for recipient in recipients:
            result = self.send_email(
                to_email=recipient['email'],
                to_name=recipient['name'],
                subject=subject,
                template_file=template_file,
                params=params,
                email_type=email_type,
                lunch_id=lunch_id,
                dry_run=dry_run
            )

            if result['success']:
                results['sent'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'email': recipient['email'],
                    'error': result['error']
                })

        return results


# Global instance
email_service = EmailService()
