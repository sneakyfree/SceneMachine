"""
Email utilities for authentication-related emails.

This module handles sending emails for:
- Password reset
- Email verification
- Account notifications
"""

import logging
from typing import Optional

from ....shared.config import get_settings

logger = logging.getLogger(__name__)


async def send_password_reset_email(
    email: str,
    username: str,
    reset_token: str,
) -> bool:
    """
    Send a password reset email to the user.

    Args:
        email: User's email address
        username: User's display name or username
        reset_token: JWT token for password reset

    Returns:
        True if email was sent successfully, False otherwise
    """
    settings = get_settings()

    # Build reset URL
    frontend_url = getattr(settings, "frontend_url", "https://app.scenemachine.com")
    reset_url = f"{frontend_url}/reset-password?token={reset_token}"

    # Email subject and body
    subject = "Reset Your SceneMachine Password"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 24px;">SceneMachine</h1>
        </div>

        <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
            <h2 style="color: #333; margin-top: 0;">Password Reset Request</h2>

            <p>Hi {username},</p>

            <p>We received a request to reset your password for your SceneMachine account. If you didn't make this request, you can safely ignore this email.</p>

            <p>To reset your password, click the button below:</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Reset Password</a>
            </div>

            <p style="color: #666; font-size: 14px;">Or copy and paste this link into your browser:</p>
            <p style="color: #667eea; font-size: 14px; word-break: break-all;">{reset_url}</p>

            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">

            <p style="color: #999; font-size: 12px;">
                This link will expire in 1 hour for security reasons.<br>
                If you didn't request a password reset, please ignore this email or contact support if you have concerns.
            </p>
        </div>

        <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
            <p>&copy; 2026 SceneMachine. All rights reserved.</p>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Password Reset Request

    Hi {username},

    We received a request to reset your password for your SceneMachine account.
    If you didn't make this request, you can safely ignore this email.

    To reset your password, visit this link:
    {reset_url}

    This link will expire in 1 hour for security reasons.

    If you didn't request a password reset, please ignore this email or contact
    support if you have concerns.

    - The SceneMachine Team
    """

    return await _send_email(
        to_email=email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )


async def send_email_verification(
    email: str,
    username: str,
    verification_token: str,
) -> bool:
    """
    Send an email verification email to the user.

    Args:
        email: User's email address
        username: User's display name or username
        verification_token: JWT token for email verification

    Returns:
        True if email was sent successfully, False otherwise
    """
    settings = get_settings()

    frontend_url = getattr(settings, "frontend_url", "https://app.scenemachine.com")
    verify_url = f"{frontend_url}/verify-email?token={verification_token}"

    subject = "Verify Your SceneMachine Email"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 24px;">SceneMachine</h1>
        </div>

        <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
            <h2 style="color: #333; margin-top: 0;">Verify Your Email</h2>

            <p>Hi {username},</p>

            <p>Welcome to SceneMachine! Please verify your email address to complete your registration.</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{verify_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Verify Email</a>
            </div>

            <p style="color: #999; font-size: 12px;">
                This link will expire in 24 hours.
            </p>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Verify Your Email

    Hi {username},

    Welcome to SceneMachine! Please verify your email address by visiting:
    {verify_url}

    This link will expire in 24 hours.

    - The SceneMachine Team
    """

    return await _send_email(
        to_email=email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )


async def _send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    from_email: Optional[str] = None,
) -> bool:
    """
    Send an email using the configured email provider.

    This is a placeholder implementation that logs the email.
    In production, integrate with:
    - SendGrid
    - AWS SES
    - Mailgun
    - Postmark
    - etc.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML email body
        text_body: Plain text email body
        from_email: Sender email (uses default if not provided)

    Returns:
        True if email was sent successfully, False otherwise
    """
    settings = get_settings()

    # Get sender email from settings or use default
    sender = from_email or getattr(
        settings, "email_from", "noreply@scenemachine.com"
    )

    # Check if email sending is enabled
    email_enabled = getattr(settings, "email_enabled", False)
    email_provider = getattr(settings, "email_provider", None)

    if not email_enabled:
        # Log email for development/testing
        logger.info(
            f"Email would be sent (email_enabled=False):\n"
            f"  To: {to_email}\n"
            f"  From: {sender}\n"
            f"  Subject: {subject}\n"
            f"  Body preview: {text_body[:200]}..."
        )
        return True

    try:
        if email_provider == "sendgrid":
            return await _send_via_sendgrid(
                to_email=to_email,
                from_email=sender,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
        elif email_provider == "ses":
            return await _send_via_ses(
                to_email=to_email,
                from_email=sender,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
        else:
            # Fallback: log the email
            logger.warning(
                f"No email provider configured, logging email:\n"
                f"  To: {to_email}\n"
                f"  Subject: {subject}"
            )
            return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


async def _send_via_sendgrid(
    to_email: str,
    from_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> bool:
    """Send email via SendGrid API."""
    try:
        # Import here to make SendGrid optional
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Content

        settings = get_settings()
        api_key = getattr(settings, "sendgrid_api_key", None)

        if not api_key:
            logger.error("SendGrid API key not configured")
            return False

        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
        )
        message.add_content(Content("text/plain", text_body))
        message.add_content(Content("text/html", html_body))

        sg = SendGridAPIClient(api_key)
        response = sg.send(message)

        return response.status_code in (200, 201, 202)

    except ImportError:
        logger.error("SendGrid library not installed: pip install sendgrid")
        return False
    except Exception as e:
        logger.error(f"SendGrid error: {e}")
        return False


async def _send_via_ses(
    to_email: str,
    from_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> bool:
    """Send email via AWS SES."""
    try:
        # Import here to make boto3 optional
        import boto3
        from botocore.exceptions import ClientError

        settings = get_settings()
        region = getattr(settings, "aws_region", "us-east-1")

        client = boto3.client("ses", region_name=region)

        response = client.send_email(
            Source=from_email,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {
                    "Text": {"Data": text_body},
                    "Html": {"Data": html_body},
                },
            },
        )

        return response.get("MessageId") is not None

    except ImportError:
        logger.error("boto3 library not installed: pip install boto3")
        return False
    except Exception as e:
        logger.error(f"AWS SES error: {e}")
        return False
