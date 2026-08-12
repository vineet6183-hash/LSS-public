"""
LSS Invoice Automation - Main Script
Automates the extraction of reduced line items from PDF and HTM invoices received via email.
Uses Microsoft Graph API — runs on GitHub Actions without a local Outlook installation.
"""

import os
import sys
import logging
from datetime import datetime
import shutil
from pathlib import Path
import re

# Import local modules
from config import *
from invoice_parser import parse_invoice
from excel_generator import create_lawsync_excel, append_to_master_tracker
from graph_client import GraphClient


def setup_logging():
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(LOG_FILE, mode='a'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()


def ensure_folders_exist():
    """Create required temp folders if they don't exist"""
    folders = [INCOMING_FOLDER, PROCESSED_FOLDER, OUTPUT_FOLDER]
    for folder in folders:
        Path(folder).mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured folder exists: {folder}")


def filter_emails(messages):
    """
    Filter Graph API messages by:
    - Sender domain: @dxc-ins.com
    - Subject exclusion: RECONSIDERATION
    - Has PDF or HTM attachments (hasAttachments flag)
    """
    filtered = []
    logger.info(f"Total unread messages: {len(messages)}")

    for msg in messages:
        try:
            sender_email = msg.get("from", {}).get("emailAddress", {}).get("address", "").lower()
            subject = msg.get("subject", "") or ""

            if SENDER_DOMAIN.lower() not in sender_email:
                logger.info(f"Skipped (wrong sender): {sender_email} | {subject}")
                continue

            if SUBJECT_EXCLUSION.upper() in subject.upper():
                logger.info(f"Excluded (RECONSIDERATION): {subject}")
                continue

            if not msg.get("hasAttachments", False):
                logger.info(f"Skipped (no attachments): {subject}")
                continue

            # Extract client from sender: lssfor(.*?)@
            client = ""
            client_match = re.search(r"lssfor(.*?)@", sender_email, re.IGNORECASE)
            if client_match:
                client = client_match.group(1).upper()

            # Parse received date
            try:
                received_dt = datetime.fromisoformat(msg["receivedDateTime"].replace("Z", "+00:00"))
                received_date = received_dt.strftime("%m/%d/%Y")
            except Exception:
                received_date = msg.get("receivedDateTime", "")

            filtered.append({
                "message_id": msg["id"],
                "subject": subject,
                "sender_email": sender_email,
                "client": client,
                "received_date": received_date
            })
            logger.info(f"Selected: '{subject}' from {sender_email} (Client: {client})")

        except Exception as e:
            logger.warning(f"Error filtering message: {e}")

    logger.info(f"Filtered {len(filtered)} emails for processing")
    return filtered


def download_invoice_attachments(graph, filtered_emails):
    """
    Download PDF and HTM attachments from filtered messages to INCOMING_FOLDER.
    Marks each processed message as read and adds the Processed-Invoice category.
    Returns list of {path, client, email_date} dicts.
    """
    downloaded = []

    for entry in filtered_emails:
        try:
            msg_id = entry["message_id"]
            attachments = graph.get_attachments(msg_id)
            has_invoice = False

            for att in attachments:
                filename = att.get("name", "")
                if not filename.lower().endswith(('.pdf', '.htm')):
                    continue

                has_invoice = True
                file_bytes = graph.get_attachment_content(msg_id, att["id"])

                filepath = os.path.join(INCOMING_FOLDER, filename)

                # Handle duplicate filenames
                counter = 1
                while os.path.exists(filepath):
                    name, ext = os.path.splitext(filename)
                    filepath = os.path.join(INCOMING_FOLDER, f"{name}_{counter}{ext}")
                    counter += 1

                with open(filepath, 'wb') as f:
                    f.write(file_bytes)

                downloaded.append({
                    'path': filepath,
                    'client': entry.get('client', ''),
                    'email_date': entry.get('received_date', '')
                })
                logger.info(f"Downloaded: {filename}")

            if has_invoice:
                try:
                    graph.mark_as_read(msg_id, categories=[PROCESSED_CATEGORY])
                    logger.info(f"Marked as read: {entry['subject']}")
                except Exception as e:
                    logger.warning(f"Failed to mark as read: {e}")

        except Exception as e:
            logger.error(
                f"Error downloading from message '{entry.get('subject', '')}': {e}",
                exc_info=True
            )

    logger.info(f"Downloaded {len(downloaded)} invoice files")
    return downloaded


def process_invoices(invoice_info_list):
    """
    Process all invoice files (PDF/HTM) and extract invoice data.
    Returns (invoice_data_list, errors).
    """
    invoice_data_list = []
    errors = []

    for info in invoice_info_list:
        file_path = info['path']
        try:
            logger.info(f"Processing: {os.path.basename(file_path)}")
            data = parse_invoice(file_path)
            if data:
                data['client'] = info['client']
                data['email_date'] = info['email_date']
                invoice_data_list.append(data)
                logger.info(f"Successfully parsed: {os.path.basename(file_path)}")
            else:
                logger.warning(f"No data extracted: {os.path.basename(file_path)}")
        except Exception as e:
            error_msg = f"Error processing {os.path.basename(file_path)}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

    logger.info(f"Successfully processed {len(invoice_data_list)} out of {len(invoice_info_list)} invoices")
    return invoice_data_list, errors


def generate_excel_output(invoice_data_list, errors):
    """Generate Excel output file in OUTPUT_FOLDER"""
    if not invoice_data_list:
        logger.warning("No invoice data to export to Excel")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"LSS_Extracted_{timestamp}.xlsx"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    success = create_lawsync_excel(invoice_data_list, output_path, EXCEL_HEADERS)

    if success:
        logger.info(f"LawSync Excel output generated: {output_path}")
        return output_path
    else:
        logger.error("Failed to generate Excel output")
        return None


def update_master_tracker(graph, invoice_data_list):
    """
    Download Master Tracker from OneDrive, append new invoice rows, and re-upload.
    Creates a new tracker file if the OneDrive download fails.
    """
    try:
        tracker_temp = os.path.join(INCOMING_FOLDER, "Master Tracker.xlsx")

        try:
            file_bytes = graph.download_onedrive_file(MASTER_TRACKER_ONEDRIVE_PATH)
            with open(tracker_temp, 'wb') as f:
                f.write(file_bytes)
            logger.info("Downloaded Master Tracker from OneDrive")
        except Exception as e:
            logger.warning(f"Could not download Master Tracker (will create new): {e}")

        success = append_to_master_tracker(
            invoice_data_list,
            tracker_temp,
            MASTER_TRACKER_HEADERS,
            MASTER_TRACKER_FORMULA
        )

        if success:
            with open(tracker_temp, 'rb') as f:
                updated_bytes = f.read()
            graph.upload_onedrive_file(MASTER_TRACKER_ONEDRIVE_PATH, updated_bytes)
            logger.info("Master Tracker uploaded back to OneDrive")

    except Exception as e:
        logger.error(f"Error updating Master Tracker: {e}", exc_info=True)


def move_to_processed(invoice_info_list):
    """Move processed invoice files to PROCESSED_FOLDER"""
    for info in invoice_info_list:
        file_path = info['path']
        try:
            filename = os.path.basename(file_path)
            dest_path = os.path.join(PROCESSED_FOLDER, filename)

            counter = 1
            while os.path.exists(dest_path):
                name, ext = os.path.splitext(filename)
                dest_path = os.path.join(PROCESSED_FOLDER, f"{name}_{counter}{ext}")
                counter += 1

            shutil.move(file_path, dest_path)
            logger.info(f"Moved to processed: {filename}")
        except Exception as e:
            logger.error(f"Error moving file {file_path}: {e}", exc_info=True)


def main():
    """Main execution workflow"""
    logger.info("=" * 80)
    logger.info("LSS Invoice Automation - Started")
    logger.info("=" * 80)

    try:
        # Step 1: Ensure temp folders exist
        logger.info("Step 1: Ensuring folder structure...")
        ensure_folders_exist()

        # Step 2: Authenticate with Microsoft Graph API
        logger.info("Step 2: Authenticating with Microsoft Graph API...")
        graph = GraphClient()

        # Step 3: Get LSS mail folder
        logger.info("Step 3: Accessing LSS mail folder...")
        folder_id = graph.get_mail_folder_id(EMAIL_FOLDER)

        # Step 4: Fetch and filter unread emails
        logger.info("Step 4: Fetching and filtering unread emails...")
        messages = graph.get_unread_messages(folder_id)
        filtered_emails = filter_emails(messages)

        if not filtered_emails:
            logger.info("No emails to process. Exiting.")
            return

        # Step 5: Download invoice attachments
        logger.info("Step 5: Downloading invoice attachments (PDF/HTM)...")
        invoice_paths = download_invoice_attachments(graph, filtered_emails)
        if not invoice_paths:
            logger.warning("No invoices downloaded. Exiting.")
            return

        # Step 6: Process invoices
        logger.info("Step 6: Processing invoices and extracting data...")
        invoice_data_list, errors = process_invoices(invoice_paths)

        # Step 7: Generate Excel output
        logger.info("Step 7: Generating Excel output...")
        output_path = generate_excel_output(invoice_data_list, errors)

        # Step 8: Update Master Tracker on OneDrive
        logger.info("Step 8: Updating Master Tracker on OneDrive...")
        if invoice_data_list:
            update_master_tracker(graph, invoice_data_list)

        # Step 9: Move files to processed folder
        logger.info("Step 9: Moving files to processed folder...")
        move_to_processed(invoice_paths)

        # Step 10: Send output email
        if output_path and OUTPUT_EMAIL:
            logger.info("Step 10: Sending output email...")
            with open(output_path, 'rb') as f:
                output_bytes = f.read()

            filename = os.path.basename(output_path)
            body = (
                f"LSS Invoice Automation completed.\n\n"
                f"Emails processed: {len(filtered_emails)}\n"
                f"Invoices downloaded: {len(invoice_paths)}\n"
                f"Data extracted from: {len(invoice_data_list)} invoices\n"
            )
            if errors:
                body += f"\nErrors ({len(errors)}):\n" + "\n".join(errors)

            graph.send_mail_with_attachment(
                to_email=OUTPUT_EMAIL,
                subject=f"LSS Automation Output - {datetime.now().strftime('%Y-%m-%d')}",
                body=body,
                filename=filename,
                file_bytes=output_bytes
            )
        elif not OUTPUT_EMAIL:
            logger.warning("OUTPUT_EMAIL not configured — skipping email send")

        # Summary
        logger.info("=" * 80)
        logger.info("LSS Invoice Automation - Completed")
        logger.info(f"Processed {len(filtered_emails)} emails")
        logger.info(f"Downloaded {len(invoice_paths)} invoices")
        logger.info(f"Extracted data from {len(invoice_data_list)} invoices")
        if output_path:
            logger.info(f"Output file: {output_path}")
        if errors:
            logger.warning(f"{len(errors)} error(s) occurred - check log for details")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Fatal error in main execution: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
