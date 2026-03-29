# Handles PDF text extraction
from pypdf import PdfReader
from io import BytesIO

def load_pdf(file_obj):
    try:
        reader = PdfReader(file_obj)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"
