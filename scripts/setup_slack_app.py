"""
Slack App Setup Guide for SIREN.

Run this to verify your Slack credentials and print the required app config.
It does NOT create the app automatically — you need to do that at api.slack.com/apps.

Usage: python scripts/setup_slack_app.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio
from siren.config import get_settings


SLACK_APP_MANIFEST = """
{
  "display_information": {
    "name": "SIREN",
    "description": "Self-Improving Incident Response Engine",
    "background_color": "#1a1a2e"
  },
  "features": {
    "bot_user": {
      "display_name": "SIREN",
      "always_online": true
    }
  },
  "oauth_config": {
    "scopes": {
      "bot": [
        "chat:write",
        "chat:write.public",
        "channels:read"
      ]
    }
  },
  "settings": {
    "interactivity": {
      "is_enabled": true,
      "request_url": "YOUR_NGROK_URL/webhook/slack/action"
    },
    "org_deploy_enabled": false,
    "socket_mode_enabled": false
  }
}
"""


async def verify_slack():
    settings = get_settings()

    print("=== SIREN Slack Setup Verification ===\n")

    if not settings.slack_bot_token:
        print("❌ SLACK_BOT_TOKEN not set in .env")
        print("   Get it from: api.slack.com/apps → Your App → OAuth & Permissions → Bot User OAuth Token")
        return

    if not settings.slack_signing_secret:
        print("❌ SLACK_SIGNING_SECRET not set in .env")
        print("   Get it from: api.slack.com/apps → Your App → Basic Information → Signing Secret")
        return

    if not settings.slack_channel_id:
        print("❌ SLACK_CHANNEL_ID not set in .env")
        print("   Right-click any Slack channel → View Channel Details → Copy Channel ID (starts with C)")
        return

    # Test the token
    try:
        from slack_sdk.web.async_client import AsyncWebClient
        client = AsyncWebClient(token=settings.slack_bot_token)
        auth = await client.auth_test()
        print(f"✅ Slack bot authenticated as: {auth['user']} (team: {auth['team']})")

        # Test channel access
        try:
            await client.chat_postMessage(
                channel=settings.slack_channel_id,
                text="🚨 SIREN connected successfully. Ready to receive incident approvals.",
            )
            print(f"✅ Test message posted to channel {settings.slack_channel_id}")
        except Exception as e:
            print(f"❌ Could not post to channel {settings.slack_channel_id}: {e}")
            print("   Make sure the bot is invited to the channel (/invite @SIREN)")
    except Exception as e:
        print(f"❌ Slack auth failed: {e}")
        return

    print("\n=== Slack App Manifest (paste at api.slack.com/apps → Create App → From Manifest) ===")
    print(SLACK_APP_MANIFEST)

    print("\n=== Required: Set the Interactivity URL ===")
    print("For local dev, use ngrok:")
    print("  1. Install ngrok: https://ngrok.com/download")
    print("  2. Run: ngrok http 8000")
    print("  3. Copy the https URL (e.g. https://abc123.ngrok.io)")
    print("  4. In Slack app settings → Interactivity → Request URL:")
    print("     https://abc123.ngrok.io/webhook/slack/action")
    print("\nFor production (Railway/Render):")
    print("  Set to: https://your-app-url.railway.app/webhook/slack/action")


if __name__ == "__main__":
    asyncio.run(verify_slack())
