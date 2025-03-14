import streamlit as st
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
import re
import logging

# Set up logging
logging.basicConfig(filename='pdf_processing.log', level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Register Arial font (ensure you have arial.ttf and arialbd.ttf in the same directory)
pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))  # Path to Arial regular font file
pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))  # Path to Arial bold font file

def extract_annexure_number(filename):
    """Extract annexure number (A1, A2, etc.) from the filename and format it as 'ANNEXURE A-X'."""
    match = re.search(r'A(\d+)', filename, re.IGNORECASE)
    if match:
        return int(match.group(1))  # Return the number as an integer for sorting
    return None

def create_annexure_overlay(pdf_path):
    """Creates an overlay PDF with annexure text on the first page."""
    filename = os.path.basename(pdf_path)
    annexure_text = f"ANNEXURE A-{extract_annexure_number(filename)}"  # Format as 'ANNEXURE A-X'

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    
    # Add annexure text (Top Right Corner)
    if annexure_text:
        can.setFont("Arial-Bold", 14)  # Set font size to 14
        text_width = can.stringWidth(annexure_text, "Arial-Bold", 14)
        # Position text at top-right corner with a small margin
        x = letter[0] - text_width - 50  # 50 is the right margin
        y = letter[1] - 50  # 50 is the top margin
        can.drawString(x, y, annexure_text.upper())  # Ensure text is in CAPITAL letters

    can.save()
    packet.seek(0)
    return packet

def create_last_page_overlay(sign_image_path):
    """Creates an overlay PDF with 'TRUE COPY' text and signature for the last page."""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    
    # Add 'TRUE COPY' text (Bottom Left)
    can.setFont("Helvetica-Bold", 14)
    can.drawString(50, 50, "TRUE COPY")

    # Add signature image (Bottom Right)
    if sign_image_path:
        sign_img = ImageReader(sign_image_path)
        can.drawImage(sign_img, 400, 50, width=150, height=50, mask='auto')

    can.save()
    packet.seek(0)
    return packet

def add_text_and_signature(input_pdf, output_pdf, sign_image_path):
    """Merge overlays with original PDF, ensuring 'ANNEXURE A-X' is on the first page and 'TRUE COPY' and signature are on the last page."""
    try:
        # Read the uploaded PDF file into a BytesIO object
        input_pdf_bytes = io.BytesIO(input_pdf.read())
        reader = PdfReader(input_pdf_bytes)
        writer = PdfWriter()
        
        # Create overlays
        annexure_overlay = create_annexure_overlay(input_pdf.name)
        last_page_overlay = create_last_page_overlay(sign_image_path)
        
        annexure_reader = PdfReader(annexure_overlay)
        last_page_reader = PdfReader(last_page_overlay)

        # Process each page
        for i, page in enumerate(reader.pages):
            if i == 0:  # First page gets Annexure text
                page.merge_page(annexure_reader.pages[0])
            if i == len(reader.pages) - 1:  # Last page gets 'TRUE COPY' and signature
                page.merge_page(last_page_reader.pages[0])
            writer.add_page(page)

        # Save the modified PDF to a BytesIO object
        output_pdf_bytes = io.BytesIO()
        writer.write(output_pdf_bytes)
        output_pdf_bytes.seek(0)
        return output_pdf_bytes
    except Exception as e:
        logging.error(f"Error processing file {input_pdf.name}: {e}")
        st.error(f"Failed to process {input_pdf.name}. Check the log file for details.")
        return None

def main():
    st.title("PDF Automation Tool")
    st.write("Upload your PDF files and signature image to process them.")

    # File uploaders
    input_files = st.file_uploader("Upload PDF Files", type="pdf", accept_multiple_files=True)
    sign_image = st.file_uploader("Upload Signature Image", type=["png", "jpg", "jpeg"])

    if input_files and sign_image:
        if st.button("Process PDFs"):
            # Sort files based on annexure number
            sorted_files = sorted(input_files, key=lambda x: extract_annexure_number(x.name))
            
            # Process individual files
            modified_files = []
            for file in sorted_files:
                try:
                    modified_pdf = add_text_and_signature(file, None, sign_image)
                    if modified_pdf:
                        modified_files.append((file.name, modified_pdf))
                except Exception as e:
                    logging.error(f"Error processing file {file.name}: {e}")
                    st.error(f"Failed to process {file.name}. Check the log file for details.")
                    continue
            
            # Merge all modified files into a single PDF with bookmarks
            if modified_files:
                try:
                    merger = PdfMerger()
                    for file_name, modified_pdf in modified_files:
                        annexure_text = f"ANNEXURE A-{extract_annexure_number(file_name)}"
                        if annexure_text:
                            # Add bookmark for the start of this PDF
                            merger.append(modified_pdf, outline_item=annexure_text)
                        else:
                            merger.append(modified_pdf)
                    
                    # Save the combined PDF to a BytesIO object
                    combined_output_bytes = io.BytesIO()
                    merger.write(combined_output_bytes)
                    combined_output_bytes.seek(0)
                    merger.close()
                    
                    # Provide download link for the combined PDF
                    st.download_button(
                        label="Download Combined PDF",
                        data=combined_output_bytes,
                        file_name="combined_output.pdf",
                        mime="application/pdf"
                    )
                    
                    st.success("PDFs processed and merged successfully!")
                except Exception as e:
                    logging.error(f"Error merging files: {e}")
                    st.error(f"Failed to merge files. Check the log file for details.")
            else:
                st.warning("No files were processed successfully.")

if __name__ == "__main__":
    main()