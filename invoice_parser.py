"""
Invoice Parser Module for LSS Invoice Automation
Handles multiple formats: PDF (via pdfplumber) and HTM (via BeautifulSoup)
Supports formats: GAIC, NARS, PMA, Progressive, SWYFTT
"""

import re
import pdfplumber
from bs4 import BeautifulSoup
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BaseInvoiceParser:
    """Base parser with common extraction logic for invoices"""
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.format_type = None
        self.full_text = ""

    def detect_format(self):
        """Detect invoice format based on content"""
        text_upper = self.full_text.upper()
        
        if "PROFESSIONAL LIABILITY" in text_upper or "GREAT AMERICAN" in text_upper or "GAIC" in text_upper:
            return "GAIC"
        elif "AMERICAN TEAM MANAGERS" in text_upper or "ATM" in text_upper:
            return "NARS"
        elif "PMA" in text_upper or "PAL" in text_upper or "SENTRY PARKWAY" in text_upper:
            return "PMA"
        elif "PROGRESSIVE" in text_upper:
            return "Progressive"
        elif "SWYFTT" in text_upper or "SWYFFT" in text_upper or "STATE NATIONAL" in text_upper:
            return "SWYFTT"
        else:
            logger.warning(f"Unknown format for {self.file_path}")
            return "UNKNOWN"

    def extract_invoice_header(self):
        """Extract invoice header information from full_text"""
        header = {
            "invoice_number": "",
            "claim_number": "",
            "company": "",
            "invoice_date": "",
            "matter_name": "",
            "auditor": "",
            "policy_holder": ""
        }
        
        # Extract Invoice Number (Prioritize Firm Invoice Number)
        # Search for Firm Invoice Number first, then Invoice ID or Firm ID
        # Labels: Firm Invoice Number, Invoice Firm ID, Invoice Firm Id, Invoice ID
        invoice_match = re.search(r"(?:Firm\s+Invoice\s+Number|Invoice\s+Firm\s+Id|Invoice\s+Firm\s+ID|Invoice\s+ID):\s*(\d+)", self.full_text, re.IGNORECASE)
        if invoice_match:
            header["invoice_number"] = invoice_match.group(1)
        
        # Extract Claim Number
        claim_match = re.search(r"Claim\s+Number:\s*([A-Z0-9-]+)", self.full_text, re.IGNORECASE)
        if not claim_match:
            # Try looking for it on the next line or with just 'Claim'
            claim_match = re.search(r"Claim:\s*([A-Z0-9-]+)", self.full_text, re.IGNORECASE)
        
        if claim_match:
            header["claim_number"] = claim_match.group(1)
        
        # Extract Company/Policy Holder
        company_match = re.search(r"Policy Holder:\s*([^\n]+)", self.full_text)
        if company_match:
            header["company"] = company_match.group(1).strip()
        else:
            company_match = re.search(r"Policy Holder:\s*\n([^\n]+)", self.full_text)
            if company_match:
                header["company"] = company_match.group(1).strip()
        
        # Extract Invoice Date
        date_match = re.search(r"Finalized Date:\s*(\d{2}/\d{2}/\d{4})", self.full_text)
        if date_match:
            header["invoice_date"] = date_match.group(1)
        else:
            date_match = re.search(r"Invoice Date:\s*(\d{2}/\d{2}/\d{4})", self.full_text)
            if date_match:
                header["invoice_date"] = date_match.group(1)
        
        # Extract Matter Name
        matter_match = re.search(r"Matter Name:\s*([^\n]+)", self.full_text)
        if matter_match:
            header["matter_name"] = matter_match.group(1).strip()
        
        # Extract Auditor
        auditor_match = re.search(r"(?:Auditor|Claim Professional|Claim Rep|Finalized By):\s*([^\n]+)", self.full_text)
        if auditor_match:
            header["auditor"] = auditor_match.group(1).strip()
        else:
            cp_match = re.search(r"Claim Professional:\s*\n([^\n]+)", self.full_text)
            if cp_match:
                header["auditor"] = cp_match.group(1).strip()
        
        # Extract Finalized Date (Appeal Exp)
        finalized_match = re.search(r"Finalized Date:\s*(\d{2}/\d{2}/\d{4})", self.full_text)
        if finalized_match:
            header["finalized_date"] = finalized_match.group(1)
        
        logger.info(f"Extracted header: Invoice {header['invoice_number']}, Claim {header['claim_number']}")
        return header

    def extract_summary_totals(self):
        """Extract Grand Total summary (Submitted, Reduction, Payable)"""
        totals = {
            "submitted": 0.0,
            "reduction": 0.0,
            "payable": 0.0
        }
        
        # Try multiple patterns for various formats
        patterns = [
            # Standard PDF Pattern: Grand Total: $123.45 $10.00 $113.45
            r"Grand Total:\s*\$([\d,.-]+)\s*\$([\d,.-]+)\s*\$([\d,.-]+)",
            # HTM Pattern: Grand Total (USD): $123.45 $10.00 $113.45
            r"Grand Total \(USD\):\s*\$([\d,.]+)\s*\$([\d,.]+)\s*\$([\d,.]+)",
            # Minimal Pattern
            r"Grand Total.*?\$([\d,.]+)\s+\$([\d,.]+)\s+\$([\d,.]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.full_text, re.IGNORECASE)
            if match:
                try:
                    totals["submitted"] = float(match.group(1).replace(',', ''))
                    totals["reduction"] = float(match.group(2).replace(',', ''))
                    totals["payable"] = float(match.group(3).replace(',', ''))
                    logger.info(f"Extracted totals: {totals}")
                    return totals
                except (ValueError, IndexError):
                    continue
        
        # If no triple match, try individual reduction match as fallback
        red_match = re.search(r"Grand Total.*?\$[\d,]+\.\d+\s+\$(\d+\.\d{2})", self.full_text)
        if red_match:
            totals["reduction"] = float(red_match.group(1).replace(',', ''))
            
        return totals

    def extract_timekeeper_mapping(self):
        """Extract timekeeper ID to name mapping"""
        mapping = {}
        summary_match = re.search(r"Timekeeper Summary\s+(.*?)(?:\n\n|\Z|Disclaimer:)", self.full_text, re.DOTALL)
        if not summary_match:
            return mapping
        
        summary_text = summary_match.group(1)
        lines = summary_text.split('\n')
        tk_pattern = r"^([A-Z0-9]+)\s+(.*?)\s+\$[\d,]+\.\d+"
        
        for line in lines:
            line = line.strip()
            match = re.match(tk_pattern, line)
            if match:
                tk_id, tk_name = match.groups()
                tk_name = tk_name.strip().rstrip(',').strip()
                mapping[tk_id] = tk_name
                
                if tk_id.isdigit():
                    name_parts = re.split(r'[\s,]+', tk_name)
                    if len(name_parts) >= 2:
                        last, first = name_parts[0], name_parts[1]
                        middle = name_parts[2] if len(name_parts) > 2 else ""
                        initials = (first[0] + middle[0] + last[0]) if middle else (first[0] + last[0])
                        mapping[initials.upper()] = tk_name
        return mapping

    def _clean_description_line(self, line):
        label_pattern = r"(?:Submitted:|Audited:|Resolution:|Payable:)\s*\$?[\d,.]+(?:\s+[\d,.]+)?(?:\s+\$[\d,.]+)?"
        rate_pattern = r"@\s*[\d,.]+\s+\$[\d,.]+"
        cleaned = re.sub(label_pattern, "", line)
        cleaned = re.sub(rate_pattern, "", cleaned)
        return cleaned.strip()

    def _is_audit_reason(self, text):
        if any(label in text for label in ['Submitted:', 'Audited:', 'Resolution:', 'Payable:']):
            return False
        keywords = ['Guideline', 'Non-Compliant', 'Overhead', 'Administrative', 'Paralegal', 'Function', 'Performed', 'Level', 'Non-Billable', 'Excess', 'Excessive', 'Vague']
        pattern = r'\b(?:' + '|'.join(keywords) + r')\b'
        return re.search(pattern, text, re.IGNORECASE) is not None

    def extract_line_items(self):
        """Extract all line items"""
        line_items = []
        flagged_match = re.search(r"Flagged Line Items\s+(.*?)(?:Timekeeper Summary|All Line Items|\Z)", self.full_text, re.DOTALL)
        
        if flagged_match:
            items_text = flagged_match.group(1)
        else:
            items_match = re.search(r"All Line Items\s+(.*?)(?:Timekeeper Summary|\Z)", self.full_text, re.DOTALL)
            if items_match:
                items_text = items_match.group(1)
            else:
                return line_items
        
        tk_mapping = self.extract_timekeeper_mapping()
        item_pattern = r"(?:\((\d+)\)\s+)?(\d{2}/\d{2}/\d{4})\s*([A-Z0-9]*)\s+(\[.*?\].*?)\s+Submitted:\s*\$([\d,]+\.\d+)\s+([\d,]+\.\d+)\s*\$([\d,]+\.\d+)"
        simple_pattern = r"(?:\((\d+)\)\s+)?(\d{2}/\d{2}/\d{4})([A-Z0-9]*)\s+(\[.*?\])\s+(.*?)\s+\$([\d,]+\.\d+)\s*@\s*([\d,]+\.\d+)\s*\$([\d,]+\.\d+)"
        
        lines = items_text.split('\n')
        i = 0
        current_section_audit_reason = ""
        collecting_audit_reason = False
        
        while i < len(lines):
            line = lines[i].strip()
            is_item_start = re.match(r"(?:\((\d+)\)\s+)?\d{2}/\d{2}/\d{4}", line)
            is_header = any(h in line for h in ['Date Initial', 'Seq Date', 'Fees', 'Expenses', 'Flagged Line Items', 'All Line Items'])
            is_audit_keyword = self._is_audit_reason(line)
            
            if is_audit_keyword and not is_item_start and not is_header:
                if not collecting_audit_reason:
                    current_section_audit_reason = line
                    collecting_audit_reason = True
                else:
                    if line not in current_section_audit_reason:
                        current_section_audit_reason += "\n" + line
            elif is_item_start or line.startswith('Note:') or line.startswith('External') or line.startswith('Reduction'):
                collecting_audit_reason = False
            elif collecting_audit_reason and not is_header and line:
                if line not in current_section_audit_reason:
                    current_section_audit_reason += "\n" + line
            
            flagged_match = re.match(item_pattern, line)
            if flagged_match:
                collecting_audit_reason = False
                seq, date, tk_initials, codes_desc, rate, units, amount = flagged_match.groups()
                last_bracket_idx = codes_desc.rfind(']')
                if last_bracket_idx != -1:
                    codes = codes_desc[:last_bracket_idx+1]
                    desc_start = codes_desc[last_bracket_idx+1:].strip()
                else:
                    codes, desc_start = codes_desc, ""
                
                item_type = self._extract_item_type(codes)
                tk_name = tk_mapping.get(tk_initials, tk_initials)
                description_lines = [desc_start]
                reduction = 0.0
                item_audit_reason = current_section_audit_reason
                
                j = i + 1
                while j < len(lines) and not re.match(r"(?:\(\d+\)\s+)?\d{2}/\d{2}/\d{4}", lines[j]):
                    next_line = lines[j].strip()
                    if not next_line: j += 1; continue
                    red_match = re.match(r"Reduction:\s*\$([\d,]+\.\d+)", next_line)
                    if red_match:
                        reduction = float(red_match.group(1).replace(',', ''))
                        break
                    if self._is_audit_reason(next_line):
                         if next_line not in item_audit_reason: item_audit_reason += "\n" + next_line
                    else:
                        cleaned = self._clean_description_line(next_line)
                        if cleaned and cleaned not in description_lines and not cleaned.startswith('Note:'):
                            description_lines.append(cleaned)
                    j += 1
                
                line_items.append({
                    "sequence": seq, "date": date, "timekeeper_id": tk_initials, "timekeeper": tk_name,
                    "item_type": item_type, "codes": codes, "description": " ".join(description_lines).strip(),
                    "rate": float(rate.replace(',','')), "units": float(units.replace(',','')), "amount": float(amount.replace(',','')),
                    "reduced_amount": reduction, "audit_reason": item_audit_reason
                })
                i = j; continue

            simple_match = re.match(simple_pattern, line)
            if simple_match:
                seq, date, tk_id, codes, desc_start, rate, units, amount = simple_match.groups()
                item_type = self._extract_item_type(codes)
                tk_name = tk_mapping.get(tk_id, f"TK-{tk_id}")
                description_lines = [desc_start]
                j = i + 1
                while j < len(lines) and not re.match(r"\(\d+\)", lines[j]) and not lines[j].strip().startswith('['):
                    if lines[j].strip(): description_lines.append(lines[j].strip())
                    j += 1
                
                line_items.append({
                    "sequence": seq, "date": date, "timekeeper_id": tk_id, "timekeeper": tk_name,
                    "item_type": item_type, "codes": codes, "description": " ".join(description_lines).strip(),
                    "rate": float(rate.replace(',','')), "units": float(units.replace(',','')), "amount": float(amount.replace(',','')),
                    "reduced_amount": 0.0, "audit_reason": ""
                })
                i = j; continue
            i += 1
        return line_items

    def _extract_item_type(self, codes):
        l_match = re.search(r'\[L(\d+)\]', codes)
        if l_match: return f"L{l_match.group(1)}"
        e_match = re.search(r'\[E(\d+)\]', codes)
        if e_match: return f"E{e_match.group(1)}"
        return codes

    def check_for_reductions(self):
        reduction_match = re.search(r"Grand Total.*?\$[\d,]+\.\d+\s+\$(\d+\.\d{2})", self.full_text)
        if reduction_match:
            reduction_amount = float(reduction_match.group(1))
            if reduction_amount > 0: return True
        return False

    def parse(self):
        logger.info(f"Parsing File: {self.file_path} (Format: {self.format_type})")
        
        # We no longer skip if reductions are zero, so that Master Tracker captures all records.
        # However, we still log it for info.
        if not self.check_for_reductions():
            logger.info("No reductions found in summary section.")
            
        return {
            "header": self.extract_invoice_header(),
            "line_items": self.extract_line_items(),
            "totals": self.extract_summary_totals(),
            "format": self.format_type
        }

class PDFParser(BaseInvoiceParser):
    """Parser for PDF files using pdfplumber"""
    def __enter__(self):
        self.pdf = pdfplumber.open(self.file_path)
        self.full_text = "\n".join([page.extract_text() or "" for page in self.pdf.pages])
        self.format_type = self.detect_format()
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'pdf') and self.pdf: self.pdf.close()

class HTMParser(BaseInvoiceParser):
    """Parser for HTM files using BeautifulSoup"""
    def __enter__(self):
        with open(self.file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
        
        # Structure-preserving text extraction
        for br in soup.find_all("br"): br.replace_with("\n")
        for tr in soup.find_all("tr"): tr.append("\n")
        
        text = soup.get_text(separator=' ')
        text = re.sub(r' +', ' ', text)
        self.full_text = re.sub(r'\n+', '\n', text)
        self.format_type = self.detect_format()
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def parse_invoice(file_path):
    """Generic function to parse either PDF or HTM invoices"""
    try:
        if file_path.lower().endswith('.pdf'):
            ParserClass = PDFParser
        elif file_path.lower().endswith('.htm'):
            ParserClass = HTMParser
        else:
            logger.error(f"Unsupported extension: {file_path}")
            return None
            
        with ParserClass(file_path) as parser:
            return parser.parse()
    except Exception as e:
        logger.error(f"Error parsing {file_path}: {str(e)}", exc_info=True)
        return None
