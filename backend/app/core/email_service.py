"""Email service for sending notifications (OTP, etc.) via Zoho Mail."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        self.base_url = settings.ALLOWED_ORIGINS.split(
            ",")[0] if settings.ALLOWED_ORIGINS else "http://localhost:5173"
        self.templates_dir = Path(__file__).parent.parent / "templates"
        self.support_email = settings.SUPPORT_EMAIL

    def render_verification_email(self, email: str, otp_code: str) -> str:
        """
        Render email verification email template.

        Args:
            email: User email address
            otp_code: 6-digit OTP code

        Returns:
            Rendered HTML email content
        """
        template_path = self.templates_dir / "verification_email.html"

        if not template_path.exists():
            # Fallback to simple HTML if template not found
            return self._simple_verification_email(email, otp_code)

        with open(template_path, "r") as f:
            template = f.read()

        # Replace template variables (no verify_url needed anymore)
        html = template.replace("{{ otp_code }}", otp_code)
        html = html.replace("{{ email }}", email)
        html = html.replace("{{ base_url }}", self.base_url)

        return html

    def _simple_verification_email(self, email: str, otp_code: str) -> str:
        """Simple verification email template optimized for deliverability."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Verify Your Email Address - DBRevel</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5; line-height: 1.6; color: #333333;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="padding: 40px 30px;">
                            <h1 style="margin: 0 0 20px 0; font-size: 24px; font-weight: 600; color: #2c3e50;">Welcome to DBRevel</h1>
                            <p style="margin: 0 0 30px 0; font-size: 16px; color: #555555;">Thank you for registering with DBRevel. To complete your registration, please verify your email address using the verification code below.</p>

                            <div style="background-color: #f8f9fa; border: 2px dashed #6a9d3a; border-radius: 8px; padding: 30px; text-align: center; margin: 30px 0;">
                                <p style="margin: 0 0 10px 0; font-size: 14px; color: #666666; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">Your Verification Code</p>
                                <p style="margin: 0; font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #6a9d3a; font-family: 'Courier New', monospace;">{otp_code}</p>
                            </div>

                            <p style="margin: 20px 0; font-size: 15px; color: #555555;">Please enter this code on the verification page to activate your account. This code will expire in 30 minutes.</p>

                            <p style="margin: 30px 0 20px 0; font-size: 14px; color: #888888; border-top: 1px solid #eeeeee; padding-top: 20px;">If you did not create an account with DBRevel, please ignore this email. No further action is required.</p>

                            <p style="margin: 20px 0 0 0; font-size: 12px; color: #aaaaaa; text-align: center;">This is an automated email. Please do not reply to this message.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    def render_otp_email(self, email: str, otp_code: str) -> str:
        """
        Render OTP email template.

        Args:
            email: User email address
            otp_code: 6-digit OTP code

        Returns:
            Rendered HTML email content
        """
        template_path = self.templates_dir / "otp_email.html"

        if not template_path.exists():
            # Fallback to simple HTML if template not found
            return self._simple_otp_email(email, otp_code)

        with open(template_path, "r") as f:
            template = f.read()

        reset_url = f"{self.base_url}/reset-password?email={email}"

        # Replace template variables
        html = template.replace("{{ otp_code }}", otp_code)
        html = html.replace("{{ email }}", email)
        html = html.replace("{{ reset_url }}", reset_url)
        html = html.replace("{{ base_url }}", self.base_url)
        html = html.replace("{{ support_email }}", self.support_email)

        return html

    def _simple_otp_email(self, email: str, otp_code: str) -> str:
        """Fallback simple OTP email if template not found."""
        reset_url = f"{self.base_url}/reset-password?email={email}"
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; background: #f4f7f1; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
                .header {{ background: linear-gradient(135deg, #6a9d3a 0%, #5a8a2f 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .otp {{ background: #f0f5eb; border: 2px solid #6a9d3a; padding: 20px; text-align: center; margin: 20px 0; font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #3a4f2a; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0ede3; font-size: 14px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>DBRevel</h1>
                </div>
                <h2>Password Reset Code</h2>
                <p>Your password reset code is:</p>
                <div class="otp">{otp_code}</div>
                <p>This code expires in 10 minutes.</p>
                <p><a href="{reset_url}" style="background: #6a9d3a; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Reset Password</a></p>
                <div class="footer">
                    <p><strong>DBRevel</strong> - AI-Powered Database SDK</p>
                    <p>Need help? Contact us at <a href="mailto:{self.support_email}" style="color: #6a9d3a;">{self.support_email}</a></p>
                    <p>If you didn't request this, please ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

    async def send_otp_email(self, email: str, otp_code: str) -> bool:
        """
        Send OTP email to user via Zoho Mail SMTP.

        Args:
            email: Recipient email address
            otp_code: OTP code to send

        Returns:
            True if email was sent successfully, False otherwise
        """
        html_content = self.render_otp_email(email, otp_code)

        # If email is disabled, log and return
        if not settings.EMAIL_ENABLED:
            logger.info(
                f"Email disabled - would send OTP {otp_code} to {email}")
            # Still save preview for development
            preview_path = Path(
                "/tmp") / f"dbrevel_email_{email.replace('@', '_at_')}.html"
            with open(preview_path, "w") as f:
                f.write(html_content)
            logger.info(f"Email preview saved to: {preview_path}")
            return True

        # Check if Zoho credentials are configured
        if not settings.ZOHO_SMTP_USER or not settings.ZOHO_SMTP_PASSWORD:
            logger.warning(
                "Zoho SMTP credentials not configured. Email not sent. "
                "Set ZOHO_SMTP_USER and ZOHO_SMTP_PASSWORD in .env"
            )
            # Save preview for development
            preview_path = Path(
                "/tmp") / f"dbrevel_email_{email.replace('@', '_at_')}.html"
            with open(preview_path, "w") as f:
                f.write(html_content)
            logger.info(f"Email preview saved to: {preview_path}")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Your DBRevel Password Reset Code"
            msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
            msg["To"] = email

            # Create HTML part
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # Create plain text fallback
            text_content = f"""
DBRevel Password Reset

Your password reset code is: {otp_code}

This code expires in 10 minutes.

Reset your password: {self.base_url}/reset-password?email={email}

If you didn't request this, please ignore this email.

---
DBRevel - AI-Powered Database SDK
"""
            text_part = MIMEText(text_content, "plain")
            msg.attach(text_part)

            # Send via Zoho SMTP
            # Use SMTP_SSL for port 465, regular SMTP for port 587
            if settings.ZOHO_SMTP_PORT == 465:
                # Port 465 uses SSL directly
                with smtplib.SMTP_SSL(settings.ZOHO_SMTP_HOST, settings.ZOHO_SMTP_PORT) as server:
                    server.login(settings.ZOHO_SMTP_USER,
                                 settings.ZOHO_SMTP_PASSWORD)
                    server.send_message(msg)
            else:
                # Port 587 uses STARTTLS
                with smtplib.SMTP(settings.ZOHO_SMTP_HOST, settings.ZOHO_SMTP_PORT) as server:
                    if settings.EMAIL_USE_TLS:
                        server.starttls()
                    server.login(settings.ZOHO_SMTP_USER,
                                 settings.ZOHO_SMTP_PASSWORD)
                    server.send_message(msg)

            logger.info(f"✅ OTP email sent successfully to {email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ Zoho SMTP authentication failed: {e}")
            logger.error(
                "Please check your ZOHO_SMTP_USER and ZOHO_SMTP_PASSWORD")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ Zoho SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(
                f"❌ Unexpected error sending email: {e}", exc_info=True)
            return False

    async def send_verification_email(self, email: str, otp_code: str) -> bool:
        """
        Send email verification email to user via Zoho Mail SMTP.

        Args:
            email: Recipient email address
            otp_code: OTP code to send

        Returns:
            True if email was sent successfully, False otherwise
        """
        html_content = self.render_verification_email(email, otp_code)

        # If email is disabled, log and return
        if not settings.EMAIL_ENABLED:
            logger.info(
                f"Email disabled - would send verification OTP {otp_code} to {email}")
            # Still save preview for development
            preview_path = Path(
                "/tmp") / f"dbrevel_verification_{email.replace('@', '_at_')}.html"
            with open(preview_path, "w") as f:
                f.write(html_content)
            logger.info(f"Email preview saved to: {preview_path}")
            return True

        # Check if Zoho credentials are configured
        if not settings.ZOHO_SMTP_USER or not settings.ZOHO_SMTP_PASSWORD:
            logger.warning(
                "Zoho SMTP credentials not configured. Email not sent. "
                "Set ZOHO_SMTP_USER and ZOHO_SMTP_PASSWORD in .env"
            )
            # Save preview for development
            preview_path = Path(
                "/tmp") / f"dbrevel_verification_{email.replace('@', '_at_')}.html"
            with open(preview_path, "w") as f:
                f.write(html_content)
            logger.info(f"Email preview saved to: {preview_path}")
            return False

        try:
            from email.utils import make_msgid

            # Create message with proper headers for deliverability
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
            msg["To"] = email
            msg["Subject"] = "Verify Your Email Address - DBRevel"
            msg["Reply-To"] = settings.EMAIL_FROM_ADDRESS
            msg["Message-ID"] = make_msgid(domain=settings.EMAIL_FROM_ADDRESS.split(
                '@')[1] if '@' in settings.EMAIL_FROM_ADDRESS else 'dbrevel.com')

            # Add headers to improve deliverability and prevent spam
            msg["X-Mailer"] = "DBRevel Email Service"
            msg["X-Priority"] = "3"
            if self.support_email:
                msg["List-Unsubscribe"] = f"<mailto:{self.support_email}?subject=Unsubscribe>"
            msg["Auto-Submitted"] = "auto-generated"

            # Create plain text alternative for better deliverability
            plain_text = f"""Welcome to DBRevel

Thank you for registering. To complete your registration, please verify your email address using the verification code below.

Your Verification Code: {otp_code}

Please enter this code on the verification page to activate your account. This code will expire in 30 minutes.

If you did not create an account with DBRevel, please ignore this email.

This is an automated email. Please do not reply to this message.
"""

            # Add plain text part first (better for spam filters)
            text_part = MIMEText(plain_text, "plain")
            msg.attach(text_part)

            # Add HTML content
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(settings.ZOHO_SMTP_HOST, settings.ZOHO_SMTP_PORT) as server:
                if settings.EMAIL_USE_TLS:
                    server.starttls()
                server.login(settings.ZOHO_SMTP_USER,
                             settings.ZOHO_SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"✓ Verification email sent to {email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ Zoho SMTP authentication failed: {e}")
            logger.error(
                "Please check your ZOHO_SMTP_USER and ZOHO_SMTP_PASSWORD")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ Zoho SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send verification email: {e}")
            return False

    def render_admin_otp_email(self, email: str, otp_code: str) -> str:
        """
        Render admin OTP email template.

        Args:
            email: Admin email address
            otp_code: 6-digit OTP code

        Returns:
            Rendered HTML email content
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; background: #f4f7f1; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #6a9d3a 0%, #5a8a2f 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .admin-badge {{ background: #ffc107; color: #333; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
                .otp {{ background: #f0f5eb; border: 2px solid #6a9d3a; padding: 20px; text-align: center; margin: 20px 0; font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #3a4f2a; border-radius: 8px; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin: 20px 0; color: #856404; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0ede3; font-size: 14px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>DBRevel Admin Login</h1>
                    <span class="admin-badge">ADMIN ACCESS</span>
                </div>
                <h2>Admin Login Code</h2>
                <p>Your admin login OTP is:</p>
                <div class="otp">{otp_code}</div>
                <p style="text-align: center; color: #666; font-size: 14px;">This code expires in 10 minutes.</p>

                <div class="warning">
                    <strong>⚠️ Security Notice:</strong> This is an admin login code for the DBRevel platform.
                    If you didn't request this, please ignore this email and contact support immediately.
                </div>

                <div class="footer">
                    <p><strong>DBRevel Platform Admin</strong></p>
                    <p>This email was sent to <strong>{email}</strong></p>
                    <p>Need help? Contact support at <a href="mailto:{self.support_email}" style="color: #6a9d3a;">{self.support_email}</a></p>
                </div>
            </div>
        </body>
        </html>
        """

    async def send_admin_otp_email(self, email: str, otp_code: str) -> bool:
        """
        Send admin OTP email via Zoho Mail SMTP.

        Args:
            email: Admin email address
            otp_code: 6-digit OTP code

        Returns:
            True if email was sent successfully, False otherwise
        """
        html_content = self.render_admin_otp_email(email, otp_code)

        # If email is disabled, log and return
        if not settings.EMAIL_ENABLED:
            logger.info(
                f"📧 Email disabled - Admin OTP for {email}: {otp_code}")
            # Save preview for development
            preview_path = Path(
                "/tmp") / f"dbrevel_admin_otp_{email.replace('@', '_at_')}.html"
            with open(preview_path, "w") as f:
                f.write(html_content)
            logger.info(f"Admin OTP email preview saved to: {preview_path}")
            logger.info(f"🔐 ADMIN OTP CODE: {otp_code}")
            return True

        # Check if Zoho credentials are configured
        if not settings.ZOHO_SMTP_USER or not settings.ZOHO_SMTP_PASSWORD:
            logger.warning(
                "Zoho SMTP credentials not configured. Admin OTP email not sent. "
                "Set ZOHO_SMTP_USER and ZOHO_SMTP_PASSWORD in .env"
            )
            # Save preview and log OTP for development
            preview_path = Path(
                "/tmp") / f"dbrevel_admin_otp_{email.replace('@', '_at_')}.html"
            with open(preview_path, "w") as f:
                f.write(html_content)
            logger.info(f"Admin OTP email preview saved to: {preview_path}")
            logger.info(f"🔐 ADMIN OTP CODE: {otp_code}")
            return False

        try:
            from email.utils import make_msgid

            # Create MIME message with proper headers
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
            msg["To"] = email
            msg["Subject"] = "DBRevel Admin Login - OTP Code"
            msg["Reply-To"] = settings.EMAIL_FROM_ADDRESS
            msg["Message-ID"] = make_msgid(domain=settings.EMAIL_FROM_ADDRESS.split(
                '@')[1] if '@' in settings.EMAIL_FROM_ADDRESS else 'dbrevel.com')
            msg["X-Mailer"] = "DBRevel Email Service"
            msg["X-Priority"] = "1"  # High priority for admin emails
            msg["Auto-Submitted"] = "auto-generated"

            # Create plain text alternative
            plain_text = f"""DBRevel Admin Login

Your admin login OTP is: {otp_code}

This code expires in 10 minutes.

⚠️ Security Notice: This is an admin login code for the DBRevel platform.
If you didn't request this, please ignore this email and contact support immediately.

This email was sent to {email}

---
DBRevel Platform Admin
"""

            # Add plain text part first
            text_part = MIMEText(plain_text, "plain")
            msg.attach(text_part)

            # Attach HTML content
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # Connect to Zoho SMTP and send
            with smtplib.SMTP(settings.ZOHO_SMTP_HOST, settings.ZOHO_SMTP_PORT) as server:
                server.starttls()
                server.login(settings.ZOHO_SMTP_USER,
                             settings.ZOHO_SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"✅ Admin OTP email sent successfully to {email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ Zoho SMTP authentication failed: {e}")
            logger.error(
                "Please check your ZOHO_SMTP_USER and ZOHO_SMTP_PASSWORD")
            logger.info(f"🔐 ADMIN OTP CODE (email failed): {otp_code}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ Zoho SMTP error: {e}")
            logger.info(f"🔐 ADMIN OTP CODE (email failed): {otp_code}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send admin OTP email: {e}")
            logger.info(f"🔐 ADMIN OTP CODE (email failed): {otp_code}")
            return False


# Global email service instance
email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service instance."""
    global email_service
    if email_service is None:
        email_service = EmailService()
    return email_service
