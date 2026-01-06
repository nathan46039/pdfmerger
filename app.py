import streamlit as st
import requests
import io
import concurrent.futures
from pypdf import PdfWriter, PdfReader

# --- Config ---
st.set_page_config(page_title="ODOT Report Merger", page_icon="📄")
BASE_URL = "https://hsip.dot.state.oh.us/api/report/"
CHUNK_SIZE = 20

# --- Helper Functions ---
def fetch_page(doc_id):
    """
    Fetches a single document by ID and returns the first page.
    Returns None if the fetch fails or the document is invalid.
    """
    url = f"{BASE_URL}{doc_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            pdf_file = io.BytesIO(response.content)
            reader = PdfReader(pdf_file)
            if len(reader.pages) > 0:
                # Return the page object. 
                # Note: The PdfReader and BytesIO stream must remain reachable 
                # for the page to be valid, which Python's GC handles here 
                # as long as the page is referenced.
                return reader.pages[0]
    except Exception:
        pass
    return None

# --- UI Layout ---
st.title("📄 ODOT Report Merger")
st.markdown(f"Enter document numbers below. The tool will merge the first page of each report and break the result into **{CHUNK_SIZE}-page PDF chunks**.")

# Input Area
raw_input = st.text_area("Document Numbers", height=200, placeholder="10234\n10235\n10236")

# Logic
if st.button("Generate PDFs", type="primary"):
    if not raw_input.strip():
        st.error("Please enter at least one document number.")
    else:
        # Progress bar setup
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Parse IDs
        doc_ids = [line.strip() for line in raw_input.replace(',', '\n').split('\n') if line.strip()]
        doc_ids = doc_ids[:300] # Limit to 300 to prevent timeouts
        
        valid_pages = []
        total = len(doc_ids)

        # 1. Fetch pages in parallel
        status_text.text(f"Starting parallel fetch for {total} documents...")
        
        # We use a list to keep track of futures to maintain order later
        futures = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # Submit all tasks
            for doc_id in doc_ids:
                future = executor.submit(fetch_page, doc_id)
                futures.append(future)
            
            # Monitor progress as tasks complete
            completed_count = 0
            for _ in concurrent.futures.as_completed(futures):
                completed_count += 1
                progress_bar.progress(completed_count / total)
                status_text.text(f"Fetching documents... ({completed_count}/{total})")
            
            # Collect results in the original order
            for future in futures:
                result = future.result()
                if result:
                    valid_pages.append(result)

        # 2. Process and Split
        if not valid_pages:
            st.error("No valid documents were found.")
            status_text.empty()
        else:
            status_text.text("Finalizing chunks...")
            st.success(f"Done! Found {len(valid_pages)} pages.")

            # Option 1: Full Download
            full_merger = PdfWriter()
            for page in valid_pages:
                full_merger.add_page(page)
            
            full_buffer = io.BytesIO()
            full_merger.write(full_buffer)
            full_bytes = full_buffer.getvalue()

            st.download_button(
                label="Download Complete PDF (All Pages)",
                data=full_bytes,
                file_name="merged_reports_full.pdf",
                mime="application/pdf",
                type="primary"
            )
            
            st.divider()
            st.subheader(f"Download by Chunk ({CHUNK_SIZE} Pages)")
            
            # Loop through pages in steps of CHUNK_SIZE
            for chunk_index, i in enumerate(range(0, len(valid_pages), CHUNK_SIZE)):
                chunk_pages = valid_pages[i : i + CHUNK_SIZE]
                
                # Create a writer for this specific chunk
                merger = PdfWriter()
                for page in chunk_pages:
                    merger.add_page(page)
                
                output_buffer = io.BytesIO()
                merger.write(output_buffer)
                pdf_bytes = output_buffer.getvalue()
                
                # Calculate labels
                start_num = i + 1
                end_num = i + len(chunk_pages)
                filename = f"merged_reports_{start_num}-{end_num}.pdf"
                
                # Display download button for this chunk
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**Part {chunk_index + 1}:** Pages {start_num} to {end_num}")
                with col2:
                    st.download_button(
                        label="Download PDF",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        key=f"btn_{chunk_index}"
                    )
            
            status_text.empty()
