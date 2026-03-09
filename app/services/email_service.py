import os
import resend
from datetime import datetime

# Initialize Resend
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
resend.api_key = RESEND_API_KEY

# The "From" email must be a verified domain in your Resend account.
# We will use SMTP_USER as the sender if it's set, otherwise fallback to a generic onboarding email.
SENDER_EMAIL = os.getenv("SMTP_USER", "onboarding@resend.dev")

def _send_email(to_email: str, subject: str, html_body: str):
    """Low-level helper: sends a single HTML email using Resend."""
    try:
        response = resend.Emails.send({
            "from": SENDER_EMAIL,
            "to": to_email,
            "subject": subject,
            "html": html_body
        })
        print(f"✅ Email sent via Resend to {to_email}. Response: {response}")
    except Exception as e:
        print(f"❌ Failed to send email via Resend to {to_email}. Error: {e}")


def send_admin_notification(emails, topic_title):
    subject = "LoopLearn — New Topic Ready for Review"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 24px;">
        <h2 style="color: #1a1a2e;">New Topic Generated</h2>
        <p>The pipeline has finished generating a new topic:</p>
        <div style="background: #f4f4f8; border-left: 4px solid #4361ee; padding: 12px 16px; margin: 16px 0;">
            <strong>{topic_title}</strong>
        </div>
        <p>Please log in to the admin panel to review and approve it.</p>
        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 24px 0;">
        <p style="font-size: 12px; color: #888;">This is an automated message from the LoopLearn pipeline.</p>
    </div>
    """

    for email in emails:
        _send_email(email, subject, html)


def send_all_domains_report(emails, result):
    """Sends a professional summary email after the all-domains pipeline completes."""
    successes = result.get("results", [])
    failures = result.get("errors", [])
    total = result.get("total_domains", 0)
    now = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")

    # Build the success rows
    success_rows = ""
    for item in successes:
        success_rows += f"""
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{item.get('domain', 'N/A')}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{item.get('topic_name', 'N/A')}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{item.get('scheduled_for', 'N/A')}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee; color: #2d6a4f;">Published</td>
        </tr>
        """

    # Build the failure rows
    failure_rows = ""
    for item in failures:
        failure_rows += f"""
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{item.get('domain', 'N/A')}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee;" colspan="2">{item.get('error', 'Unknown error')}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #eee; color: #d00000;">Failed</td>
        </tr>
        """

    # Status banner
    if failures:
        banner_color = "#e76f51"
        banner_text = f"{len(successes)}/{total} domains succeeded — {len(failures)} failed"
    else:
        banner_color = "#2d6a4f"
        banner_text = f"All {total} domains completed successfully"

    subject = f"LoopLearn Daily Pipeline Report — {len(successes)}/{total} Domains Completed"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 700px; margin: auto; padding: 24px;">
        <h2 style="color: #1a1a2e; margin-bottom: 4px;">Daily Pipeline Report</h2>
        <p style="color: #666; margin-top: 0;">{now}</p>

        <div style="background: {banner_color}; color: #fff; padding: 12px 16px; border-radius: 6px; margin: 16px 0;">
            {banner_text}
        </div>

        <h3 style="color: #1a1a2e;">Published Topics</h3>
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <thead>
                <tr style="background: #f4f4f8;">
                    <th style="padding: 8px 12px; text-align: left;">Domain</th>
                    <th style="padding: 8px 12px; text-align: left;">Topic</th>
                    <th style="padding: 8px 12px; text-align: left;">Scheduled For</th>
                    <th style="padding: 8px 12px; text-align: left;">Status</th>
                </tr>
            </thead>
            <tbody>
                {success_rows if success_rows else '<tr><td colspan="4" style="padding: 8px 12px; color: #888;">No topics were published.</td></tr>'}
                {failure_rows}
            </tbody>
        </table>

        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 24px 0;">
        <p style="font-size: 12px; color: #888;">This is an automated report from the LoopLearn pipeline. No action is needed for successfully published topics.</p>
    </div>
    """

    for email in emails:
        _send_email(email, subject, html)
