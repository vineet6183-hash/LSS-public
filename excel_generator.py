"""
Excel Generator Module for LSS Invoice Automation
Creates Excel files in BillSync format
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ExcelGenerator:
    """Generate Excel output in BillSync format"""
    
    def __init__(self, output_path, headers):
        self.output_path = output_path
        self.headers = headers
        self.workbook = openpyxl.Workbook()
        self.worksheet = self.workbook.active
        self.worksheet.title = "Line Items"
        self.current_row = 1
    
    def format_headers(self):
        """Apply formatting to header row"""
        # Define styles
        header_font = Font(bold=True, size=11, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        border_side = Side(style="thin", color="000000")
        border = Border(left=border_side, right=border_side, top=border_side, bottom=border_side)
        
        # Write and format headers
        for col_idx, header in enumerate(self.headers, start=1):
            cell = self.worksheet.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border
        
        # Set row height
        self.worksheet.row_dimensions[1].height = 30
        
        logger.debug("Headers formatted")
    
    def populate_data_rows(self, invoice_data_list):
        """
        Populate worksheet with line item data
        
        Args:
            invoice_data_list: List of parsed invoice data dictionaries
        """
        row_idx = 2  # Start after header
        
        for invoice_data in invoice_data_list:
            if not invoice_data:
                continue
            
            header = invoice_data.get("header", {})
            line_items = invoice_data.get("line_items", [])
            
            # Extract header info (Only use what's needed for requested fields)
            invoice_number = header.get("invoice_number", "")
            invoice_date = header.get("invoice_date", "")
            
            for item in line_items:
                # Selective Filtering: Ignore line items where reduction is zero
                reduced_amount = item.get("reduced_amount", 0)
                if reduced_amount <= 0:
                    continue
                
                # Map extracted data to the 22-column structure
                # 1. Invoice Number
                # 2. Company (IGNORE)
                # 3. User (IGNORE)
                # 4. Invoice Date
                # 5. Working Timekeeper
                # 6. Billing Timekeeper
                # 7. Description (Empty)
                # 8. Date of Item
                # 9. Last Date to add Attorney Information
                # 10. Appeal Status
                # 11. Matter Number (IGNORE)
                # 12. Task ID
                # 13. Item Type
                # 14. UNITS
                # 15. RATE
                # 16. AMOUNT
                # 17. Reduced Amount
                # 18. Total Invoice Amount
                # 19. Narrative (Consolidated description starting after bracket + Audit Reason)
                # 20. Attorney Comment (Audit Reason)
                # 21. Attachment
                # 22. Attachment : URL
                
                # Format Narrative: Description + \n + 'Audit Reason : ' + Audit Reason
                description = item.get("description", "")
                audit_reason = item.get("audit_reason", "")
                narrative = description
                if audit_reason:
                    narrative += f"\nAudit Reason : {audit_reason}"

                # Item Type logic: 'Fees' if Initials are not Blank else 'Expenses'
                tk_initials = item.get("timekeeper_id", "").strip()
                item_type_display = "Fees" if tk_initials else "Expenses"

                values = [
                    invoice_number,                          # 1
                    "",                                      # 2 (Ignore Company)
                    "",                                      # 3 (Ignore User)
                    invoice_date,                            # 4
                    item.get("timekeeper", ""),              # 5 (Full Name)
                    "",                                      # 6
                    "",                                      # 7
                    item.get("date", ""),                    # 8
                    "",                                      # 9
                    "",                                      # 10
                    "",                                      # 11 (Ignore Matter Number)
                    "",                                      # 12
                    item_type_display,                       # 13 (Fees/Expenses)
                    item.get("units", 0),                    # 14
                    item.get("rate", 0),                     # 15
                    item.get("amount", 0),                   # 16
                    item.get("reduced_amount", 0),           # 17
                    "",                                      # 18
                    narrative,                               # 19
                    "",                                      # 20 (Keep Blank)
                    "",                                      # 21
                    ""                                       # 22
                ]
                
                # Write values to row
                for col_idx, value in enumerate(values, start=1):
                    cell = self.worksheet.cell(row=row_idx, column=col_idx)
                    cell.value = value
                    
                    # Format currency columns
                    if col_idx in [15, 16, 17]:  # RATE, AMOUNT, Reduced Amount
                        cell.number_format = '$#,##0.00'
                    
                    # Format Units
                    if col_idx == 14:  # UNITS
                        cell.number_format = '0.00'
                    
                    # Center align date and units
                    if col_idx in [4, 8, 14]:  # Invoice Date, Date of Item, UNITS
                        cell.alignment = Alignment(horizontal="center")
                
                row_idx += 1
        
        total_rows = row_idx - 2
        logger.info(f"Populated {total_rows} data rows")
        return total_rows
    
    def apply_column_widths(self):
        """Auto-adjust column widths for readability"""
        # Define column widths for all 22 columns
        column_widths = {
            'A': 15, 'B': 25, 'C': 20, 'D': 15, 'E': 25, 
            'F': 25, 'G': 15, 'H': 15, 'I': 15, 'J': 15,
            'K': 20, 'L': 15, 'M': 15, 'N': 10, 'O': 12,
            'P': 12, 'Q': 15, 'R': 15, 'S': 60, 'T': 40,
            'U': 15, 'V': 30
        }
        
        for col_letter, width in column_widths.items():
            if col_letter in self.worksheet.column_dimensions:
                self.worksheet.column_dimensions[col_letter].width = width
            else:
                # Add default width for columns beyond dictionary if needed
                self.worksheet.column_dimensions[col_letter].width = 15
        
        # Explicitly set Narrative and Attorney Comment widths
        self.worksheet.column_dimensions['S'].width = 60
        self.worksheet.column_dimensions['T'].width = 40
        
        logger.debug("Column widths applied")

    
    def save(self):
        """Save the workbook to file"""
        try:
            self.workbook.save(self.output_path)
            logger.info(f"Excel file saved: {self.output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving Excel file: {str(e)}", exc_info=True)
            return False


def create_billsync_excel(invoice_data_list, output_path, headers):
    """
    Main function to create BillSync format Excel file
    
    Args:
        invoice_data_list: List of parsed invoice data dictionaries
        output_path: Path where Excel file should be saved
        headers: List of column headers
    
    Returns:
        True if successful, False otherwise
    """
    try:
        generator = ExcelGenerator(output_path, headers)
        
        # Format headers
        generator.format_headers()
        
        # Populate data
        total_rows = generator.populate_data_rows(invoice_data_list)
        
        # Apply column widths
        generator.apply_column_widths()
        
        # Save file
        return generator.save()
        
    except Exception as e:
        logger.error(f"Error creating Excel file: {str(e)}", exc_info=True)
        return False


def append_to_master_tracker(invoice_data_list, tracker_path, headers, formula_template):
    """
    Append summary data to the Master Tracker Excel file
    
    Args:
        invoice_data_list: List of parsed invoice data dictionaries
        tracker_path: Path to the Master Tracker Excel file
        headers: List of column headers for the tracker
        formula_template: Formula for the 'ExistInMaster' column
    """
    try:
        import os
        from openpyxl import load_workbook, Workbook
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(tracker_path), exist_ok=True)
        
        if os.path.exists(tracker_path):
            wb = load_workbook(tracker_path)
            ws = wb.active
        else:
            wb = Workbook()
            ws = wb.active
            ws.title = "Invoices"
            # Write headers
            for col_idx, header in enumerate(headers, start=1):
                ws.cell(row=1, column=col_idx).value = header
        
        start_row = ws.max_row + 1
        current_row = start_row
        
        for data in invoice_data_list:
            if not data:
                continue
            
            header = data.get("header", {})
            totals = data.get("totals", {})
            
            # Map internal keys to headers
            # headers: ['Email Date', 'Invoice', 'Invoice Date', 'Invoice Amount', 
            #           'Total Adjustment', 'Approved Total', 'ExistInMaster', 'Client', 'Appeal Exp']
            
            row_data = {
                'Email Date': data.get('email_date', ''),
                'Invoice': header.get('invoice_number', ''),
                'Invoice Date': header.get('invoice_date', ''),
                'Invoice Amount': totals.get('submitted', 0),
                'Total Adjustment': totals.get('reduction', 0),
                'Approved Total': totals.get('payable', 0),
                'ExistInMaster': formula_template.format(row=current_row),
                'Client': data.get('client', ''),
                'Appeal Exp': header.get('finalized_date', '')
            }
            
            for col_idx, h in enumerate(headers, start=1):
                cell = ws.cell(row=current_row, column=col_idx)
                val = row_data.get(h, '')
                
                # Handle formula
                if h == 'ExistInMaster':
                    cell.value = val
                else:
                    cell.value = val
                
                # Formatting
                if h in ['Invoice Amount', 'Total Adjustment', 'Approved Total']:
                    cell.number_format = '$#,##0.00'
                elif h in ['Email Date', 'Invoice Date', 'Appeal Exp']:
                    cell.alignment = Alignment(horizontal="center")
            
            current_row += 1
            
        wb.save(tracker_path)
        logger.info(f"Appended {len(invoice_data_list)} records to Master Tracker: {tracker_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error appending to Master Tracker: {str(e)}", exc_info=True)
        return False
