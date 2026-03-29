# Handles file ingestion and text processing
from pypdf import PdfReader
from io import BytesIO

class IngestionHandler:
    @staticmethod
    def load_pdf(file_obj) -> str:
        """Extracts text from a uploaded PDF file object."""
        try:
            reader = PdfReader(file_obj)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""

    @staticmethod
    def chunk_text(text, chunk_size=1000, chunk_overlap=200) -> list:
        """Splits text into manageable chunks with overlap."""
        if not text:
            return []
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + chunk_size
            if end < text_len:
                # Try to break at a newline
                last_newline = text.rfind('\n', start, end)
                if last_newline != -1 and last_newline > start + chunk_size * 0.5:
                    end = last_newline + 1
                else:
                    # Fallback to space
                    last_space = text.rfind(' ', start, end)
                    if last_space != -1 and last_space > start + chunk_size * 0.5:
                        end = last_space + 1
            
            chunk = text[start:end]
            chunks.append(chunk)
            
            # Move start forward, accounting for overlap
            start += chunk_size - chunk_overlap
            
            # Prevent infinite loops if progress isn't made
            if chunk_size <= chunk_overlap:
                 start += 1
                 
        return chunks
