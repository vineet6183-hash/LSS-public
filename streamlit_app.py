"""
LSS Invoice → LawSync Streamlit App
Upload PDF invoices from the LSS Portal and download a LawSync-format Excel file.
"""

import io
import os
import tempfile
import logging
import streamlit as st
import openpyxl

from invoice_parser import parse_invoice
from excel_generator import create_lawsync_excel
from config import EXCEL_HEADERS

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Password protection ───────────────────────────────────────────────────────
# Set APP_PASSWORD in Streamlit secrets (secrets.toml) or as an environment variable.
# The app will refuse to start if no password is configured.
def _get_app_password() -> str:
    # Streamlit Cloud secrets take precedence
    try:
        return st.secrets["APP_PASSWORD"]
    except (KeyError, FileNotFoundError):
        pass
    pwd = os.environ.get("APP_PASSWORD", "")
    if not pwd:
        st.error(
            "APP_PASSWORD is not configured. "
            "Set it in Streamlit secrets or as an environment variable before deploying."
        )
        st.stop()
    return pwd


def check_password() -> bool:
    """Return True if the user has entered the correct password."""
    if st.session_state.get("authenticated"):
        return True

    st.title("LSS Invoice → LawSync")
    st.subheader("Please enter the access password")

    with st.form("login_form"):
        pwd = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if pwd == _get_app_password():
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")

    return False


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_uploaded_pdf(uploaded_file) -> dict | None:
    """Save uploaded file to a temp path and parse it."""
    suffix = ".pdf" if uploaded_file.name.lower().endswith(".pdf") else ".htm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    try:
        return parse_invoice(tmp_path)
    finally:
        os.unlink(tmp_path)


def build_excel_bytes(invoice_data_list: list) -> bytes:
    """Generate LawSync Excel in memory and return raw bytes."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp_path = tmp.name

    try:
        create_lawsync_excel(invoice_data_list, tmp_path, EXCEL_HEADERS)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def render_summary(invoice_data: dict, filename: str):
    """Render a compact summary card for one parsed invoice."""
    header = invoice_data.get("header", {})
    totals = invoice_data.get("totals", {})
    items = invoice_data.get("line_items", [])
    reduced_items = [i for i in items if i.get("reduced_amount", 0) > 0]

    with st.expander(f"**{filename}** — Invoice #{header.get('invoice_number', 'N/A')}", expanded=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("Submitted", f"${totals.get('submitted', 0):,.2f}")
        col2.metric("Reduction", f"${totals.get('reduction', 0):,.2f}")
        col3.metric("Payable", f"${totals.get('payable', 0):,.2f}")

        info_cols = st.columns(2)
        info_cols[0].write(f"**Format:** {invoice_data.get('format', 'Unknown')}")
        info_cols[0].write(f"**Invoice Date:** {header.get('invoice_date', '—')}")
        info_cols[0].write(f"**Claim #:** {header.get('claim_number', '—')}")
        info_cols[1].write(f"**Policy Holder:** {header.get('company', '—')}")
        info_cols[1].write(f"**Auditor:** {header.get('auditor', '—')}")
        info_cols[1].write(f"**Reduced Line Items:** {len(reduced_items)} of {len(items)}")


# ── Main app ──────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="LSS Invoice → LawSync",
        page_icon="📄",
        layout="wide",
    )

    if not check_password():
        st.stop()

    # Sidebar – logout
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/invoice.png", width=60)
        st.title("LSS LawSync Tool")
        st.markdown("Upload one or more LSS Portal PDF invoices to extract data in LawSync format.")
        st.divider()
        if st.button("🔒 Logout"):
            st.session_state.clear()
            st.rerun()

    st.title("📄 LSS Invoice → LawSync Extractor")
    st.markdown(
        "Upload **PDF invoices** from the LSS Portal. The app will parse each invoice "
        "and produce a single **LawSync-format Excel** file ready for download."
    )

    uploaded_files = st.file_uploader(
        "Drop PDF invoices here",
        type=["pdf"],
        accept_multiple_files=True,
        help="Supported formats: GAIC, NARS, PMA, Progressive, SWYFTT",
    )

    if not uploaded_files:
        st.info("Upload at least one PDF invoice to get started.")
        return

    st.divider()

    # ── Parse ────────────────────────────────────────────────────────────────
    results: list[tuple[str, dict | None]] = []

    with st.spinner("Parsing invoices…"):
        for uf in uploaded_files:
            data = parse_uploaded_pdf(uf)
            results.append((uf.name, data))

    # ── Summaries ────────────────────────────────────────────────────────────
    success_data = []
    errors = []

    for filename, data in results:
        if data:
            render_summary(data, filename)
            success_data.append(data)
        else:
            errors.append(filename)

    if errors:
        st.warning(f"Could not parse {len(errors)} file(s): {', '.join(errors)}")

    if not success_data:
        st.error("No invoices were successfully parsed. Please check your files.")
        return

    # ── Generate & download Excel ─────────────────────────────────────────────
    st.divider()
    st.subheader("Download LawSync Excel")

    total_reduced = sum(
        len([i for i in d.get("line_items", []) if i.get("reduced_amount", 0) > 0])
        for d in success_data
    )
    st.write(f"Ready to export **{total_reduced} reduced line items** from **{len(success_data)} invoice(s)**.")

    if total_reduced == 0:
        st.warning("No line items with reductions found across the uploaded invoices. The Excel file will be empty.")

    try:
        excel_bytes = build_excel_bytes(success_data)
        st.download_button(
            label="⬇️ Download LawSync Excel",
            data=excel_bytes,
            file_name="LawSync_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
    except Exception as e:
        st.error(f"Failed to generate Excel: {e}")
        logger.exception("Excel generation error")


if __name__ == "__main__":
    main()
