# DesFlyer Email Automation System

DesFlyer Email Automation System is a Flask-based email automation
platform designed to manage email campaigns, sender accounts,
recipients, sending jobs, reports, and analytics from a single
application.

The project can be run as a web application during development and can
also be packaged as a Windows desktop application (`.exe`) using
PyInstaller.

## Features

### Email Campaign Management

-   Create and manage email campaigns
-   Define email subject and message content
-   Add multiple recipients
-   Support for To, CC, and BCC
-   Support for email attachments
-   Recipient validation and duplicate handling
-   Campaign status tracking

### Automated Email Sending

-   Background campaign worker
-   Controlled sending flow
-   Configurable delay between emails
-   Retry handling for failed sends
-   Pause and resume campaign processing
-   Individual email delivery status tracking

### Sender Management

-   Configure SMTP sender accounts
-   Store sender-specific SMTP configuration securely
-   Support SMTP authentication
-   Sender account management through the application

### Reports

-   Campaign-level email reports
-   Sent and failed email counts
-   Recipient-level delivery status
-   Email history and details
-   Report views based on completed sending results

### Analytics

-   Campaign performance statistics
-   Sent/failed delivery metrics
-   Campaign history
-   Overall email activity analysis

### Desktop Application

The project can be packaged into a Windows executable using PyInstaller.

The desktop version: - Runs without manually starting the Flask
development server - Uses a local desktop launcher - Stores persistent
application data outside the PyInstaller temporary directory - Keeps the
SQLite database in the user's Windows AppData directory - Can be moved
to another folder on the same computer without losing application data

## Technology Stack

  Component                   Technology
  --------------------------- -----------------------
  Backend                     Python, Flask
  Database                    SQLite
  ORM                         SQLAlchemy
  Frontend                    HTML, CSS, JavaScript
  Email                       SMTP
  Background processing       Python worker
  Desktop packaging           PyInstaller
  Desktop server              Waitress
  Environment configuration   `.env`
  Version control             Git / GitHub

## Project Structure

``` text
DesFlyer-Email-Automation/
│
├── app.py
├── config.py
├── create_admin.py
├── worker.py
│
├── models/
│   ├── campaign.py
│   └── sender_email.py
│
├── routes/
│   ├── dashboard.py
│   └── email.py
│
├── services/
│   ├── campaign_service.py
│   └── email_service.py
│
├── templates/
│   ├── analytics.html
│   ├── base.html
│   ├── campaign_detail.html
│   ├── campaign_history.html
│   ├── dashboard.html
│   ├── email_detail.html
│   ├── email_history.html
│   ├── report.html
│   ├── send_email.html
│   └── settings.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── script.js
│
├── database/
├── instance/
│
├── desktop_launcher.py
├── desktop_build.bat
├── DesFlyer.spec
├── requirements.txt
├── requirements-desktop.txt
├── smoke_checks.py
├── DESKTOP_BUILD.md
├── .env.example
└── .gitignore
```

## Application Flow

``` text
User Login
    ↓
Dashboard
    ↓
Configure Sender
    ↓
Create Campaign
    ↓
Add / Validate Recipients
    ↓
Compose Email
    ↓
Start Campaign
    ↓
Background Worker
    ↓
SMTP Sender
    ↓
Email Delivery
    ↓
Update Recipient Status
    ↓
Campaign Report
    ↓
Analytics
```

The worker processes recipients individually so that each email can have
its own delivery status.

Typical recipient states include:

``` text
PENDING
   ↓
SENDING
   ↓
SENT

or

SENDING
   ↓
FAILED
   ↓
RETRY
   ↓
SENT / FAILED
```

## Desktop Data Storage

The desktop `.exe` should not use the PyInstaller temporary extraction
directory for persistent data.

Persistent DesFlyer data is stored under:

``` text
%LOCALAPPDATA%\DesFlyer\
```

Typical structure:

``` text
%LOCALAPPDATA%\DesFlyer\
│
├── database\
│   └── desflyer.db
│
├── secret.key
└── .env
```

This allows the executable to be moved or replaced without losing
application data.

## Installation --- Development Mode

### 1. Clone the repository

``` bash
git clone <repository-url>
cd DesFlyer-Email-Automation
```

### 2. Create a virtual environment

Windows PowerShell:

``` powershell
python -m venv .venv
```

Activate it:

``` powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution for the current session:

``` powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Then activate again:

``` powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

``` powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file based on `.env.example`.

Do not commit the real `.env` file to GitHub.

Example:

``` env
SECRET_KEY=your-secret-key
CAMPAIGN_UNSUBSCRIBE_BASE_URL=https://your-public-domain.example
```

SMTP sender settings should be configured through the application's
sender settings rather than committing credentials to source control.

### 5. Initialize the application

If a fresh installation requires an administrator account, use the
project's admin initialization process.

### 6. Run the application

``` powershell
python app.py
```

Open the local application in your browser using the address shown by
Flask.

## Building the Windows `.exe`

The repository includes a desktop build script.

From the project root:

``` powershell
.\desktop_build.bat
```

The script builds:

``` text
dist\
└── DesFlyer-Email-Automation.exe
```

The PyInstaller specification is:

``` text
DesFlyer.spec
```

### Running the executable

You can run the generated executable directly:

``` powershell
.\dist\DesFlyer-Email-Automation.exe
```

The desktop launcher starts the local application and serves it through
the packaged environment.

## Desktop Database Migration

The desktop version supports persistent local data.

On first launch, the application checks for the desktop database
location and initializes or migrates the database as required.

This prevents the common PyInstaller one-file problem where application
data is written to a temporary extraction directory.

## Testing

Basic project smoke checks are available in:

``` text
smoke_checks.py
```

Run:

``` powershell
python smoke_checks.py
```

Before sending a real campaign, test with email addresses that you
control.

Recommended test flow:

``` text
Login
 ↓
Dashboard
 ↓
Configure SMTP sender
 ↓
Create test campaign
 ↓
Add test recipient
 ↓
Send
 ↓
Verify recipient status
 ↓
Check Report
 ↓
Check Analytics
```

Also test:

-   Invalid email address
-   Duplicate recipient
-   SMTP authentication failure
-   Failed email
-   Retry
-   Pause campaign
-   Resume campaign
-   Application restart
-   Attachment
-   CC/BCC
-   Multiple recipients
-   Database persistence

## Email Deliverability

The application includes controlled sending and campaign processing
features intended to support responsible email delivery.

However, no application can guarantee that emails will never enter spam.

Inbox placement depends on factors including:

-   SMTP provider reputation
-   Sender reputation
-   Domain reputation
-   SPF, DKIM, and DMARC configuration
-   IP reputation
-   Recipient engagement
-   Email content
-   Sending volume and patterns
-   Recipient complaints and bounces

For production email campaigns, use a properly authenticated sending
domain and follow the policies of your email provider.

For real campaigns, configure a public HTTPS unsubscribe endpoint if
unsubscribe links are enabled.

## Security

Do not commit sensitive information to GitHub.

Never commit:

``` text
.env
*.db
*.sqlite
*.key
.venv/
build/
dist/
__pycache__/
```

SMTP passwords and other credentials should be kept outside source
control.

The `.gitignore` file is configured to exclude local environment files,
databases, keys, virtual environments, and generated desktop build
files.

## Git Workflow

Example development workflow:

``` powershell
git status
git add .
git commit -m "Describe your changes"
git push origin email-software-development
```

Keep feature development on a separate branch when appropriate and merge
into the main branch only after testing.

## Production Recommendations

Before using the system for production campaigns:

1.  Use a verified sending domain.
2.  Configure SPF.
3.  Configure DKIM.
4.  Configure DMARC.
5.  Use a reputable SMTP/email provider.
6.  Start with controlled sending volumes.
7.  Monitor bounces and failures.
8.  Provide an unsubscribe mechanism where required.
9.  Keep SMTP credentials out of source control.
10. Test campaigns with controlled recipients before production sending.

## Limitations

-   The desktop build is currently intended for Windows.
-   SMTP provider configuration is required for email delivery.
-   A public HTTPS URL is required for externally accessible unsubscribe
    functionality.
-   The application does not guarantee inbox placement.
-   The `.exe` and local database are separate: moving the `.exe` on the
    same PC does not move the user's AppData database.

## License

This project is proprietary to DesFlyer unless a separate license is
provided.

## Author

**DesFlyer**

Email Automation System
