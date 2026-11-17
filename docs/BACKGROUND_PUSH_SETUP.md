# SYLUS background message and push setup

The private API and browser push support are implemented. Background generation uses the GitHub Actions schedule in `.github/workflows/proactive-messages.yml`; delivery to a closed app uses Web Push.

## 1. Configure the scheduler secret

Generate a random value locally:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set that same value in:
- Render web service environment: `SCHEDULER_SECRET`
- GitHub repository → Settings → Secrets and variables → Actions → New repository secret: `SYLUS_SCHEDULER_SECRET`

Also add a GitHub Actions repository secret named `SYLUS_BASE_URL` with the private service URL:
`https://sylus-companion-private-gbcz.onrender.com`

The workflow checks every 15 minutes. The server still enforces the owner’s enabled setting, 90-minute idle threshold, four-hour minimum interval, Dhaka quiet hours, and its own natural-message decision.

## 2. Enable push notifications on a device

The Render service has a VAPID key pair configured. Sign in to SYLUS on the device, open Settings → Push notifications, and choose **Enable notifications on this device**. Grant the browser notification permission.

The private server stores only the push endpoint and encryption keys. It removes expired subscriptions automatically.

## 3. Android note

For reliable Android delivery, install SYLUS from the browser menu using **Add to Home screen**. Android may still apply battery restrictions to the browser; allow background activity/notifications for the browser if delivery is delayed.

Do not commit VAPID private keys or the scheduler secret to this repository.
