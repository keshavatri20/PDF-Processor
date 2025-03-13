from flask import Flask, request, send_file, render_template
import fitz  # PyMuPDF
import os
import tempfile

app = Flask(__name__)

# Temporary folder for uploaded files
UPLOAD_FOLDER = tempfile.mkdtemp()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def modify_individual_pdfs(pdf_files, sign_image_path):
    modified_pdfs = []
    for pdf in pdf_files:
        doc = fitz.open(pdf)
        # Step 1: Add "Annexure X" to the first page
        annexure_text = f"Annexure {os.path.basename(pdf)[-1]}"
        first_page = doc[0]
        first_page.insert_text((first_page.rect.width - 120, 30), annexure_text, fontsize=12, color=(0, 0, 0))
        
        # Step 2: Add "True Copy" to the last page
        last_page = doc[-1]
        last_page.insert_text((50, last_page.rect.height - 50), "True Copy", fontsize=12, color=(0, 0, 0))
        
        # Step 3: Add signature image to the last page
        if sign_image_path and os.path.exists(sign_image_path):
            rect = fitz.Rect(last_page.rect.width - 100, last_page.rect.height - 50, last_page.rect.width - 10, last_page.rect.height - 10)
            last_page.insert_image(rect, filename=sign_image_path)
        
        # Save the modified PDF
        modified_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"modified_{os.path.basename(pdf)}")
        doc.save(modified_pdf_path)
        doc.close()
        modified_pdfs.append(modified_pdf_path)
    
    return modified_pdfs

def merge_pdfs(pdf_files, output_pdf):
    merged_doc = fitz.open()
    toc = []
    page_count = 0
    for pdf in pdf_files:
        doc = fitz.open(pdf)
        merged_doc.insert_pdf(doc)
        toc.append((1, os.path.basename(pdf), page_count + 1))  # Store TOC information
        page_count += len(doc)
        doc.close()
    merged_doc.set_toc(toc)  # Set all bookmarks at once
    merged_doc.save(output_pdf)
    merged_doc.close()
    return output_pdf

def add_page_numbers(pdf_path, output_path):
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        text = str(i + 1)
        page.insert_text((page.rect.width - 50, 30), text, fontsize=12, color=(0, 0, 0))
    doc.save(output_path)
    doc.close()
    return output_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_pdfs():
    if 'pdfs' not in request.files:
        return "No PDF files uploaded!", 400
    pdf_files = request.files.getlist('pdfs')
    sign_image = request.files.get('signature')
    
    # Save uploaded files
    pdf_paths = []
    for pdf in pdf_files:
        if pdf and allowed_file(pdf.filename):
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf.filename)
            pdf.save(pdf_path)
            pdf_paths.append(pdf_path)
    
    sign_image_path = None
    if sign_image and allowed_file(sign_image.filename):
        sign_image_path = os.path.join(app.config['UPLOAD_FOLDER'], sign_image.filename)
        sign_image.save(sign_image_path)
    
    # Process PDFs
    modified_pdfs = modify_individual_pdfs(pdf_paths, sign_image_path)
    merged_path = os.path.join(app.config['UPLOAD_FOLDER'], 'merged_output.pdf')
    merge_pdfs(modified_pdfs, merged_path)
    final_output = os.path.join(app.config['UPLOAD_FOLDER'], 'final_output.pdf')
    add_page_numbers(merged_path, final_output)
    
    # Send the final file to the user
    return send_file(final_output, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)