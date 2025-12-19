import streamlit as st
import requests
import io
from pypdf import PdfWriter, PdfReader

# --- Config ---
st.set_page_config(page_title="ODOT Report Merger", page_icon="📄")
BASE_URL = "https://hsip.dot.state.oh.us/api/report/"

# --- UI Layout ---
st.title("📄 ODOT Report Merger")
st.markdown("Enter document numbers below to merge the first page of each report into a single PDF.")

# Input Area
raw_input = st.text_area("Document Numbers", height=200, placeholder="10234\n10235\n10236")

# Logic
if st.button("Generate PDF", type="primary"):
    if not raw_input.strip():
        st.error("Please enter at least one document number.")
    else:
        # Progress bar setup
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Parse IDs
        doc_ids = [line.strip() for line in raw_input.replace(',', '\n').split('\n') if line.strip()]
        doc_ids = doc_ids[:300] # Limit to 300
        
        merger = PdfWriter()
        success_count = 0
        total = len(doc_ids)

        # Loop
        for i, doc_id in enumerate(doc_ids):
            status_text.text(f"Processing {doc_id} ({i+1}/{total})...")
            url = f"{BASE_URL}{doc_id}"
            
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    pdf_file = io.BytesIO(response.content)
                    reader = PdfReader(pdf_file)
                    if len(reader.pages) > 0:
                        merger.add_page(reader.pages[0])
                        success_count += 1
            except Exception:
                pass # Skip errors silently to keep UI clean
            
            # Update progress
            progress_bar.progress((i + 1) / total)

        # Finalize
        if success_count > 0:
            output_buffer = io.BytesIO()
            merger.write(output_buffer)
            pdf_bytes = output_buffer.getvalue()
            
            st.success(f"Done! {success_count} reports merged.")
            st.download_button(
                label="Download Final PDF",
                data=pdf_bytes,
                file_name="merged_reports.pdf",
                mime="application/pdf"
            )
        else:
            st.error("No valid documents were found.")