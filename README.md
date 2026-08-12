# LSS Invoice Automation

Automates the extraction of reduced line items from PDF invoice attachments received via email from `@dxc-ins.com`. The script filters emails, parses PDFs in multiple formats, and generates Excel output in LawSync format.

## Features

- ✅ **Automated Email Processing**: Connects to Outlook and processes emails from the LSS folder
- ✅ **Smart Filtering**: 
  - Filters emails from `@dxc-ins.com` domain
  - Excludes emails with "RECONSIDERATION" in subject
  - Processes only unread emails to avoid duplicates
- ✅ **Multi-Format PDF Support**: Handles 5 different invoice formats (GAIC, NARS, PMA, Progressive, SWYFTT)
- ✅ **Intelligent Data Extraction**:
  - Invoice header information (Invoice Number, Claim Number, Company, etc.)
  - Line item details (Timekeeper, Date, Item Type, Description, Rate, Units, Amount, etc.)
  - Timekeeper ID to Name mapping
- ✅ **Excel Output**: Generates formatted Excel files in LawSync style
- ✅ **File Management**: Automatically moves processed PDFs to archive folder
- ✅ **Comprehensive Logging**: Detailed logs for debugging and audit trail

## Folder Structure

```
LSS/
├── lss_invoice_automation.py   # Main script
├── pdf_parser.py                # PDF parsing module
├── excel_generator.py           # Excel generation module
├── config.py                    # Configuration settings
├── requirements.txt             # Python dependencies
├── lss_automation.log          # Log file (created at runtime)
└── Sample PDF/                 # Sample PDF files for testing
    ├── GAIC/
    ├── NARS/
    ├── PMA/
    ├── Progressive/
    └── SWYFTT/
```

## Output Folders

The script uses the following OneDrive folders:

- **Incoming**: `C:\Users\EliteAdm\OneDrive - GMD\General - Appeals\LSS\Invoices_Incoming`
  - PDFs are downloaded here from emails
  
- **Processed**: `C:\Users\EliteAdm\OneDrive - GMD\General - Appeals\LSS\Invoices_Processed`
  - PDFs are moved here after successful processing
  
- **Output**: `C:\Users\EliteAdm\OneDrive - GMD\General - Appeals\LSS\Output_Excel`
  - Generated Excel files are saved here with timestamp

## Installation

1. **Install Python Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

2. **Verify Outlook Setup**:
   - Ensure Microsoft Outlook is installed and configured
   - The LSS folder should be accessible in your Outlook account
   - LSS is a separate folder at the same level as Inbox (not a subfolder)

## Usage

### Basic Usage

Run the automation script:

```powershell
python lss_invoice_automation.py
```

The script will:
1. Connect to Outlook
2. Access the LSS folder
3. Filter unread emails from `@dxc-ins.com` (excluding RECONSIDERATION)
4. Download PDF attachments to Incoming folder
5. Parse PDFs and extract line item data
6. Generate Excel file in Output folder
7. Move processed PDFs to Processed folder
8. Mark emails as read

### Test Mode (Manual Processing)

To test with sample PDFs without email processing:

1. Copy sample PDFs to the Incoming folder:
   ```powershell
   Copy-Item "e:\Antigravity Workspace\LSS\Sample PDF\GAIC\*.pdf" "C:\Users\EliteAdm\OneDrive - GMD\General - Appeals\LSS\Invoices_Incoming"
   ```

2. Comment out the email processing steps in `lss_invoice_automation.py` and add:
   ```python
   # Get PDFs from incoming folder instead
   pdf_paths = [os.path.join(INCOMING_FOLDER, f) for f in os.listdir(INCOMING_FOLDER) if f.endswith('.pdf')]
   ```

## Configuration

Edit `config.py` to customize settings:

```python
# Email Settings
EMAIL_FOLDER = "LSS"
SENDER_DOMAIN = "@dxc-ins.com"
SUBJECT_EXCLUSION = "RECONSIDERATION"

# Folder Paths
INCOMING_FOLDER = r"C:\Users\EliteAdm\OneDrive - GMD\General - Appeals\LSS\Invoices_Incoming"
PROCESSED_FOLDER = r"C:\Users\EliteAdm\OneDrive - GMD\General - Appeals\LSS\Invoices_Processed"
OUTPUT_FOLDER = r"C:\Users\EliteAdm\OneDrive - GMD\General - Appeals\LSS\Output_Excel"
```

## Excel Output Format

The generated Excel file includes:

**Line Items Sheet**:
- Invoice Number
- Claim Number
- Company
- Timekeeper
- Date
- Item Type
- Description/Narrative
- Units
- Rate
- Amount
- Reduced Amount
- Audit Reason

**Summary Sheet**:
- Processing date and time
- Total PDFs processed
- Total line items extracted
- Error list (if any)

## Logging

All operations are logged to `lss_automation.log` with:
- Timestamp
- Log level (INFO, WARNING, ERROR)
- Detailed messages
- Stack traces for errors

View the log file to troubleshoot issues or verify processing.

## Troubleshooting

### "LSS folder not found"

**Issue**: Script cannot find the LSS folder in Outlook.

**Solutions**:
- Verify the folder name in Outlook matches "LSS" exactly (case-sensitive)
- Ensure LSS is at the root level, not inside Inbox
- Check that Outlook is running and properly connected

### "No emails to process"

**Issue**: No emails match the filtering criteria.

**Possible Causes**:
- All matching emails are already read
- No emails from `@dxc-ins.com` domain
- All emails contain "RECONSIDERATION" in subject
- No PDF attachments in emails

**Solutions**:
- Check the email filtering criteria in `config.py`
- Manually mark some test emails as unread
- Verify sender email domains

### "Error parsing PDF"

**Issue**: PDF format not recognized or extraction failed.

**Solutions**:
- Check if PDF is password-protected or corrupted
- Verify PDF format matches one of the supported types
- Review the log file for specific error details
- The PDF might have a new format that needs parser updates

### "Permission denied" when moving files

**Issue**: Cannot move files to Processed folder.

**Solutions**:
- Ensure the OneDrive folder paths exist
- Check file permissions on the folders
- Close any programs that might have the PDF open
- Verify OneDrive is syncing properly

## Scheduled Automation

To run the script automatically on a schedule:

### Option 1: Windows Task Scheduler

1. Open Task Scheduler
2. Create New Task
3. Set trigger (e.g., daily at 9:00 AM)
4. Set action: 
   - Program: `python.exe`
   - Arguments: `"e:\Antigravity Workspace\LSS\lss_invoice_automation.py"`
   - Start in: `"e:\Antigravity Workspace\LSS"`

### Option 2: Batch Script

Create a batch file `run_automation.bat`:

```batch
@echo off
cd /d "e:\Antigravity Workspace\LSS"
python lss_invoice_automation.py
pause
```

## Support

For issues or questions:
1. Check the `lss_automation.log` file for detailed error messages
2. Review the troubleshooting section above
3. Verify all configuration settings in `config.py`

## Version History

- **v1.0** (2026-01-06): Initial release
  - Email filtering from @dxc-ins.com
  - Multi-format PDF parsing (GAIC, NARS, PMA, Progressive, SWYFTT)
  - Excel output in LawSync format
  - Automated file management
