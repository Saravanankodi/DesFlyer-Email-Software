# DesFlyer Email Automation — Windows Desktop Build

## What this does

The desktop build keeps the existing Flask UI and email worker, but runs both locally and opens the application in a native desktop window.

- UI: Flask + HTML/CSS/JavaScript
- Local server: Waitress on `127.0.0.1:5173`
- Background worker: existing campaign worker in a background thread
- Database: SQLite in `%LOCALAPPDATA%\DesFlyer\database\desflyer.db` when packaged
- SMTP passwords: encrypted using the persistent DesFlyer secret key
- Packaging: PyInstaller one-file `.exe`

## Build on Windows

1. Install Python 3.10+.
2. Open Command Prompt in the project folder.
3. Run:

```bat
desktop_build.bat
```

The executable will be:

```text
dist\DesFlyer-Email-Automation.exe
```

## First launch

The application creates its persistent data directory automatically:

```text
%LOCALAPPDATA%\DesFlyer\
    database\desflyer.db
    secret.key
    .env          (optional)
```

The existing project database can be copied into the `database` folder before first launch if you want to retain existing data.

## SMTP setup

Use the application's sender settings for sender-specific SMTP configuration. Do not hard-code SMTP passwords into source code.

## Unsubscribe URL

For real email campaigns, configure:

```text
CAMPAIGN_UNSUBSCRIBE_BASE_URL=https://your-public-https-domain.example
```

A desktop-only `localhost` URL cannot be reached by recipients, so it must not be used as the production unsubscribe URL.

## Test checklist

Before sending real emails:

- Login works.
- Add a sender and SMTP credentials.
- Send one test email to an address you control.
- Verify the message is received and the campaign changes to `COMPLETED`.
- Verify the Email Report contains the final result.
- Verify Analytics counts match the report.
- Upload a CSV and an XLSX recipient list.
- Verify invalid and duplicate addresses are handled correctly.
- Test pause/resume with at least a few recipients.
- Test a deliberately invalid SMTP configuration and verify the campaign fails/pauses without silently marking recipients as sent.
- Test an unsubscribe URL only after configuring a public HTTPS URL.
