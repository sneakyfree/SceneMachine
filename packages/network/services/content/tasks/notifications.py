"""
Notification tasks for SceneMachine Network.

Handles sending email and push notifications for various events:
- Video processing complete
- New follower
- Comment on video
- Payout processed
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from celery.utils.log import get_task_logger

from .celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    name="services.content.tasks.notifications.send_email_notification_task",
    max_retries=3,
    default_retry_delay=60,
)
def send_email_notification_task(
    self,
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> dict:
    """
    Send an email notification.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML body
        text_content: Plain text body (optional fallback)

    Returns:
        Dict with send result
    """
    logger.info(f"Sending email to {to_email}: {subject}")

    try:
        # Get SMTP settings from environment
        smtp_host = os.environ.get("SMTP_HOST", "localhost")
        smtp_port = int(os.environ.get("SMTP_PORT", "1025"))
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_password = os.environ.get("SMTP_PASSWORD", "")
        from_email = os.environ.get("EMAIL_FROM", "noreply@scenemachine.network")

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email

        # Add text and HTML parts
        if text_content:
            msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_user and smtp_password:
                server.starttls()
                server.login(smtp_user, smtp_password)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {to_email}")

        return {
            "to": to_email,
            "subject": subject,
            "status": "sent",
        }

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="services.content.tasks.notifications.send_push_notification_task",
    max_retries=3,
    default_retry_delay=30,
)
def send_push_notification_task(
    self,
    user_id: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
    icon: Optional[str] = None,
    url: Optional[str] = None,
) -> dict:
    """
    Send a push notification to a user.

    Args:
        user_id: UUID of the recipient user
        title: Notification title
        body: Notification body
        data: Additional data payload
        icon: Notification icon URL
        url: Click action URL

    Returns:
        Dict with send result
    """
    logger.info(f"Sending push notification to user {user_id}: {title}")

    try:
        # In production, this would:
        # 1. Look up user's push subscription(s) from database
        # 2. Send via Web Push API or FCM/APNs

        # For now, just log the notification
        logger.info(
            f"Push notification for {user_id}: {title} - {body}"
        )

        # Placeholder for actual push implementation
        # from pywebpush import webpush
        # subscriptions = get_user_push_subscriptions(user_id)
        # for sub in subscriptions:
        #     webpush(
        #         subscription_info=sub,
        #         data=json.dumps({
        #             "title": title,
        #             "body": body,
        #             "icon": icon,
        #             "url": url,
        #             "data": data,
        #         }),
        #         vapid_private_key=VAPID_PRIVATE_KEY,
        #         vapid_claims={"sub": "mailto:push@scenemachine.network"}
        #     )

        return {
            "user_id": user_id,
            "title": title,
            "status": "sent",
        }

    except Exception as e:
        logger.error(f"Failed to send push notification to {user_id}: {e}")
        raise self.retry(exc=e)


# =============================================================================
# NOTIFICATION TEMPLATES
# =============================================================================


def send_video_ready_notification(user_id: str, video_title: str, video_url: str):
    """Send notification when video processing is complete."""
    send_email_notification_task.delay(
        to_email="",  # Would look up user's email
        subject=f"Your video '{video_title}' is ready!",
        html_content=f"""
        <h1>Your video is ready!</h1>
        <p>Great news! Your video <strong>{video_title}</strong> has finished processing
        and is now live on SceneMachine Network.</p>
        <p><a href="{video_url}">Watch your video</a></p>
        """,
    )
    send_push_notification_task.delay(
        user_id=user_id,
        title="Video Ready!",
        body=f"Your video '{video_title}' is now live",
        url=video_url,
    )


def send_new_follower_notification(user_id: str, follower_name: str, follower_url: str):
    """Send notification when someone follows the user."""
    send_push_notification_task.delay(
        user_id=user_id,
        title="New Follower",
        body=f"{follower_name} started following you",
        url=follower_url,
    )


def send_comment_notification(
    user_id: str,
    commenter_name: str,
    video_title: str,
    comment_preview: str,
    video_url: str,
):
    """Send notification when someone comments on user's video."""
    send_push_notification_task.delay(
        user_id=user_id,
        title=f"New comment on '{video_title}'",
        body=f"{commenter_name}: {comment_preview[:100]}...",
        url=video_url,
    )


def send_payout_notification(
    user_id: str,
    user_email: str,
    amount: float,
    currency: str = "USD",
):
    """Send notification when payout is processed."""
    send_email_notification_task.delay(
        to_email=user_email,
        subject=f"Payout of ${amount:.2f} {currency} processed",
        html_content=f"""
        <h1>Payout Processed</h1>
        <p>Your payout of <strong>${amount:.2f} {currency}</strong> has been processed
        and should arrive in your bank account within 2-5 business days.</p>
        <p><a href="https://scenemachine.network/creator/earnings">View your earnings</a></p>
        """,
    )
    send_push_notification_task.delay(
        user_id=user_id,
        title="Payout Processed",
        body=f"${amount:.2f} {currency} is on its way to your bank",
        url="/creator/earnings",
    )


def send_milestone_notification(
    user_id: str,
    milestone_type: str,
    count: int,
):
    """Send notification when user reaches a milestone."""
    milestones = {
        "views": f"🎉 Your videos have reached {count:,} total views!",
        "followers": f"🎉 You now have {count:,} followers!",
        "earnings": f"🎉 You've earned ${count:,.2f} on SceneMachine Network!",
    }

    body = milestones.get(milestone_type, f"🎉 Milestone reached: {count:,}!")

    send_push_notification_task.delay(
        user_id=user_id,
        title="Milestone Reached!",
        body=body,
        url="/creator/dashboard",
    )
