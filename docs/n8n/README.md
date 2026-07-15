# Ovulite Module 1 — n8n setup

Import `ovulite-module-1-data-intake.json` into n8n and configure:

- `OVULITE_API_URL` — normally `http://backend:8000` in Docker Compose.
- `OVULITE_API_TOKEN` — a restricted admin/embryologist service token.
- `OVULITE_SLACK_CHANNEL` — quarantine notification channel.
- `OVULITE_ALERT_FROM` and `OVULITE_ALERT_TO` — validation-summary email addresses.
- Slack and SMTP credentials on their respective nodes.

Connect an S3, Google Drive, SFTP, or Dropbox trigger to the HTTP Request node if
the webhook is not used. The source connector must provide the upload in binary
property `data` and its original filename. Ovulite performs the authoritative
hashing, immutable persistence, schema validation, quarantine, and reporting;
n8n orchestrates source connectors and notifications without duplicating rules.
