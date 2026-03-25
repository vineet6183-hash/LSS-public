# LSS Invoice Automation Configuration

import os
import tempfile

# Email Settings
EMAIL_FOLDER = "LSS"  # Separate folder at the same level as Inbox
SENDER_DOMAIN = "dxc-ins.com"
SUBJECT_EXCLUSION = "RECONSIDERATION"
PROCESSED_CATEGORY = "Processed-Invoice"

# Output Settings
OUTPUT_EMAIL = os.environ.get("OUTPUT_EMAIL", "")

# OneDrive path for Master Tracker (relative to drive root, no leading slash)
MASTER_TRACKER_ONEDRIVE_PATH = os.environ.get(
    "MASTER_TRACKER_ONEDRIVE_PATH",
    "General - Appeals/LSS/OUTPUT/Master Tracker.xlsx"
)

# Temp folder paths (used on GitHub Actions runner)
_TEMP = tempfile.gettempdir()
INCOMING_FOLDER = os.path.join(_TEMP, "lss_incoming")
PROCESSED_FOLDER = os.path.join(_TEMP, "lss_processed")
OUTPUT_FOLDER = os.path.join(_TEMP, "lss_output")

# Log File
LOG_FILE = "lss_automation.log"

# Excel Column Headers (BillSync Format from Sample BillSync.xlsx)
EXCEL_HEADERS = [
    'Invoice Number',
    'Company',
    'User',
    'Invoice Date',
    'Working Timekeeper',
    'Billing Timekeeper',
    'Description',
    'Date of Item',
    'Last Date to add Attorney Information',
    'Appeal Status',
    'Matter Number',
    'Task ID',
    'Item Type',
    'UNITS',
    'RATE',
    'AMOUNT',
    'Reduced Amount',
    'Total Invoice Amount',
    'Narrative',
    'Attorney Comment',
    'Attachment',
    'Attachment : URL'
]

# Master Tracker Headers
MASTER_TRACKER_HEADERS = [
    'Email Date',
    'Invoice',
    'Invoice Date',
    'Invoice Amount',
    'Total Adjustment',
    'Approved Total',
    'ExistInMaster',
    'Client',
    'Appeal Exp'
]

# Master Tracker Formula
MASTER_TRACKER_FORMULA = "=ISNA(MATCH(B{row}, 'https://gmdcom.sharepoint.com/sites/Appeals/Shared Documents/General/[Master Appeal Tracker (Ver. 2).xlsx]Master'!$C:$C,0))"


# PDF Format Detection Keywords
FORMAT_KEYWORDS = {
    "GAIC": ["Great American", "GAIC"],
    "NARS": ["AMERICAN TEAM MANAGERS", "ATM"],
    "PMA": ["PMA"],
    "Progressive": ["Progressive"],
    "SWYFTT": ["SWYFTT", "Swyfft"]
}

# Item Type Code Mapping (from codes like [L160], [E112])
ITEM_TYPE_CODES = {
    "L": "Legal Fees",
    "E": "Expense",
    "A": "Activity"
}
