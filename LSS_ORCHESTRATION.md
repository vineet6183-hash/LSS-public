# LSS Invoice Automation — Full Orchestration Flow

```
===============================================================================================
  LSS INVOICE AUTOMATION — END-TO-END FLOW
  From: Email Arrives in LSS Folder
  To:   Output Excel sent to rajit@scan-logic.com
===============================================================================================
```

---

## Architecture Overview

```
┌─────────────────────┐        ┌──────────────────────┐        ┌──────────────────────────┐
│   MICROSOFT 365     │        │    POWER AUTOMATE     │        │     GITHUB ACTIONS        │
│                     │        │                       │        │                           │
│  Email arrives in   │──────► │  Trigger: New email   │──────► │  Run Python Script        │
│  LSS Outlook Folder │        │  in LSS folder        │        │  lss_invoice_automation.py│
│                     │        │  → HTTP POST to GitHub│        │                           │
└─────────────────────┘        └──────────────────────┘        └──────────────────────────┘
                                                                           │
                                                                           ▼
                                                                ┌──────────────────────────┐
                                                                │  OUTPUT                  │
                                                                │  ✅ Excel → OneDrive     │
                                                                │  ✅ Master Tracker updated│
                                                                │  ✅ Email to rajit@...   │
                                                                └──────────────────────────┘
```

---

## Trigger Layer — Power Automate

```
┌─────────────────────────────────────────────────────────────────────┐
│  POWER AUTOMATE FLOW: "LSS Invoice Trigger"                         │
│                                                                     │
│  TRIGGER:                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ When a new email arrives (V3)                               │   │
│  │  • Folder   : LSS (vineet@scan-logic.com)                  │   │
│  │  • Attachment: Required                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                          │                                          │
│                          ▼                                          │
│  ACTION:                                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ HTTP POST → GitHub API                                      │   │
│  │  URL    : api.github.com/repos/vineet6183-hash/LSS/         │   │
│  │           dispatches                                        │   │
│  │  Header : Authorization: Bearer {GITHUB_TOKEN}             │   │
│  │  Body   : { "event_type": "run-lss-automation" }           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Execution Layer — GitHub Actions

```
┌─────────────────────────────────────────────────────────────────────┐
│  GITHUB ACTIONS WORKFLOW: lss_automation.yml                        │
│                                                                     │
│  TRIGGERS:                                                          │
│   • repository_dispatch (from Power Automate)   ← Real-time        │
│   • schedule: 0 14 * * 1-5  (9AM EST weekdays)  ← Fallback        │
│   • workflow_dispatch (manual)                   ← Debug           │
│                                                                     │
│  ENVIRONMENT SECRETS:                                               │
│   • AZURE_TENANT_ID      = c1af9a0a-e80e-...                       │
│   • AZURE_CLIENT_ID      = 090438ad-828f-...                       │
│   • AZURE_CLIENT_SECRET  = Hlc8Q~...                               │
│   • USER_EMAIL           = vineet@scan-logic.com                   │
│   • OUTPUT_EMAIL         = rajit@scan-logic.com                    │
│   • MASTER_TRACKER_PATH  = Appeals/Documents/General/LSS/          │
│                            OUTPUT/Master Tracker.xlsx               │
│                                                                     │
│  STEPS:                                                             │
│   1. Checkout repository                                            │
│   2. Set up Python 3.11                                             │
│   3. Install dependencies (msal, requests, pdfplumber,             │
│      beautifulsoup4, openpyxl)                                      │
│   4. Run lss_invoice_automation.py                                  │
│   5. Upload lss_automation.log as artifact                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Processing Layer — Python Script

### Step 1 — Ensure Folder Structure

```
lss_invoice_automation.py → main()
│
├── Creates local temp folders on GitHub runner:
│     /tmp/lss/incoming/
│     /tmp/lss/processed/
│     /tmp/lss/output/
```

### Step 2 — Authenticate with Microsoft Graph

```
graph_client.py → GraphClient.__init__() → _authenticate()
│
├── Uses MSAL (Microsoft Authentication Library)
├── Credentials: TENANT_ID + CLIENT_ID + CLIENT_SECRET
├── Scope: https://graph.microsoft.com/.default
└── Returns: Bearer Token for all subsequent API calls
```

### Step 3 — Access LSS Mail Folder

```
graph_client.py → get_mail_folder_id(folder_name="LSS")
│
├── API: GET /v1.0/users/{USER_EMAIL}/mailFolders
│         ?$filter=displayName eq 'LSS'
└── Returns: folder_id (used in next step)
```

### Step 4 — Fetch Unread Emails

```
graph_client.py → get_unread_messages(folder_id)
│
├── API: GET /v1.0/users/{USER_EMAIL}/mailFolders/{folder_id}/messages
│         ?$filter=isRead eq false
│         &$select=id,subject,from,receivedDateTime,hasAttachments
│
├── FILTER (config.py):
│     ✅ Sender domain must be: @dxc-ins.com
│     ✅ Subject must contain keywords (invoice-related)
│     ❌ Exclude: "do not reply", "notification", etc.
│
└── Returns: List of matching email message objects
```

### Step 5 — Download Attachments

```
graph_client.py → list_attachments(message_id)
                → download_attachment(message_id, attachment_id)
│
├── API: GET /v1.0/users/{USER_EMAIL}/messages/{id}/attachments
│
├── Supported formats:
│     • .pdf  → saved to /tmp/lss/incoming/
│     • .htm  → saved to /tmp/lss/incoming/
│
└── Skips: images, .msg files, unrelated attachments
```

### Step 6 — Parse Invoice Files

```
invoice_parser.py → BaseInvoiceParser.parse(file_path)
│
├── DETECT FORMAT:
│     • GAIC       → keywords: ["gaic", "great american"]
│     • NARS       → keywords: ["nars", "national association"]
│     • PMA        → keywords: ["pma"]
│     • Progressive→ keywords: ["progressive"]
│     • SWYFTT     → keywords: ["swyftt", "swift"]
│
├── PDF FILES → PDFParser (pdfplumber)
│     └── Extracts text page by page
│
├── HTM FILES → HTMParser (BeautifulSoup)
│     └── Parses HTML tables and text nodes
│
├── EXTRACTED DATA:
│     • Invoice Number
│     • Claim Number
│     • Invoice Date
│     • Auditor Name
│     • Client Name / Matter
│     • Line Items:
│         - Timekeeper name & code
│         - Item type (fee/expense)
│         - Hours billed / Hours allowed
│         - Rate billed / Rate allowed
│         - Amount billed / Amount allowed
│         - Reduction amount
│         - Audit reason/code
│
└── Returns: Structured invoice data dict
```

### Step 7 — Generate Excel Output

```
excel_generator.py → ExcelGenerator.generate(invoice_data)
│
├── FORMAT: LawSync (22 columns)
│     Columns:
│     A  - Invoice Number        M  - Rate Billed
│     B  - Claim Number          N  - Rate Allowed
│     C  - Invoice Date          O  - Amount Billed
│     D  - Auditor               P  - Amount Allowed
│     E  - Client                Q  - Reduction Amount
│     F  - Matter                R  - Reduction %
│     G  - Timekeeper Name       S  - Audit Reason
│     H  - Timekeeper Code       T  - Item Type Code
│     I  - Item Type             U  - Hours Billed
│     J  - Hours Allowed         V  - Hours Reduction
│     K  - Hours Reduction %
│     L  - Hours Reduction Reason
│
├── STYLING:
│     • Header row: Blue background, white bold text
│     • Data rows: Auto-width columns
│     • Currency columns: $#,##0.00 format
│     • Only includes line items with reduction > 0
│
└── Saves to: /tmp/lss/output/LSS_Output_{timestamp}.xlsx
```

### Step 8 — Update Master Tracker on OneDrive

```
excel_generator.py → append_to_master_tracker(invoice_data)
graph_client.py    → download_onedrive_file() / upload_onedrive_file()
│
├── DOWNLOAD:
│     API: GET /v1.0/users/{USER_EMAIL}/drive/root:
│               /Appeals/Documents/General/LSS/OUTPUT/Master Tracker.xlsx:/content
│
├── APPEND new rows with summary data from invoice
│
└── UPLOAD back:
│     API: PUT /v1.0/users/{USER_EMAIL}/drive/root:
│               /Appeals/Documents/General/LSS/OUTPUT/Master Tracker.xlsx:/content
```

### Step 9 — Mark Emails as Read & Move Files

```
graph_client.py → mark_message_as_read(message_id)
│
├── API: PATCH /v1.0/users/{USER_EMAIL}/messages/{id}
│       Body: { "isRead": true }
│
└── Moves local files:
      /tmp/lss/incoming/ → /tmp/lss/processed/
```

### Step 10 — Send Output Email

```
graph_client.py → send_email(to, subject, body, attachments)
│
├── API: POST /v1.0/users/{USER_EMAIL}/sendMail
│
├── TO      : rajit@scan-logic.com
├── FROM    : vineet@scan-logic.com
├── SUBJECT : "LSS Invoice Output — {date}"
├── BODY    : Summary of processed invoices
└── ATTACH  : LSS_Output_{timestamp}.xlsx
```

---

## Complete End-to-End Flow Diagram

```
  vineet@scan-logic.com (LSS folder)
          │
          │  New email from @dxc-ins.com arrives
          │
          ▼
  ┌─────────────────────┐
  │   POWER AUTOMATE    │
  │   Detects new email │
  │   in LSS folder     │
  └─────────┬───────────┘
            │ HTTP POST
            │ event_type: run-lss-automation
            ▼
  ┌─────────────────────┐
  │   GITHUB ACTIONS    │
  │   Spins up runner   │
  │   Installs Python   │
  └─────────┬───────────┘
            │
            ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                    PYTHON SCRIPT                            │
  │                                                             │
  │  [Auth]──►[Get LSS Folder]──►[Fetch Unread Emails]         │
  │                                        │                   │
  │                              [Filter by domain/subject]    │
  │                                        │                   │
  │                              [Download Attachments]        │
  │                              (.pdf / .htm)                 │
  │                                        │                   │
  │                              [Parse Invoices]              │
  │                              (GAIC/NARS/PMA/Progressive/   │
  │                               SWYFTT formats)              │
  │                                        │                   │
  │                              [Generate Excel]              │
  │                              (LawSync 22-column format)   │
  │                                        │                   │
  │                    ┌───────────────────┤                   │
  │                    │                   │                   │
  │                    ▼                   ▼                   │
  │          [Update Master Tracker] [Mark emails read]        │
  │          (OneDrive)                                        │
  │                    │                   │                   │
  │                    └───────────────────┤                   │
  │                                        │                   │
  │                              [Send Email]                  │
  └────────────────────────────────────────┼────────────────── ┘
                                           │
                                           ▼
                              rajit@scan-logic.com
                              📧 LSS Invoice Output — {date}
                              📎 LSS_Output_{timestamp}.xlsx
```

---

## Secrets & Credentials Map

| Secret | Used By | Purpose |
|---|---|---|
| `AZURE_TENANT_ID` | graph_client.py | MSAL auth — identifies your M365 org |
| `AZURE_CLIENT_ID` | graph_client.py | MSAL auth — identifies the app |
| `AZURE_CLIENT_SECRET` | graph_client.py | MSAL auth — app password |
| `USER_EMAIL` | graph_client.py | Mailbox to read emails from |
| `OUTPUT_EMAIL` | lss_invoice_automation.py | Where to send the output |
| `MASTER_TRACKER_ONEDRIVE_PATH` | excel_generator.py | OneDrive file path |
| `GITHUB_TOKEN` | Power Automate | Trigger GitHub Actions via API |

---

## Schedule Summary

| Trigger | When | How |
|---|---|---|
| **Real-time** | Every new LSS email | Power Automate → GitHub API |
| **Scheduled fallback** | Mon–Fri 9:00 AM EST | GitHub Actions cron |
| **Manual** | On-demand | GitHub Actions UI → Run workflow |

---

## File Structure

```
LSS/
├── lss_invoice_automation.py   ← Main orchestrator
├── graph_client.py             ← Microsoft Graph API wrapper
├── invoice_parser.py           ← PDF/HTM invoice parser
├── excel_generator.py          ← Excel output + Master Tracker
├── config.py                   ← All settings & constants
├── requirements.txt            ← Python dependencies
├── LSS_ORCHESTRATION.md        ← This file
└── .github/
    └── workflows/
        └── lss_automation.yml  ← GitHub Actions workflow
```

---

*Last updated: 2026-03-25*
