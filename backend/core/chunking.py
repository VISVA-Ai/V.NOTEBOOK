# Handles text chunking logic
def recursive_split_text(text, chunk_size=1000, chunk_overlap=200):
    if not text:
        return []
    
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        if end < text_len:
            last_newline = text.rfind('\n', start, end)
            if last_newline != -1 and last_newline > start + chunk_size * 0.5:
                end = last_newline + 1
            else:
                last_space = text.rfind(' ', start, end)
                if last_space != -1 and last_space > start + chunk_size * 0.5:
                    end = last_space + 1
        
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - chunk_overlap
        if chunk_size <= chunk_overlap:
             start += 1
             
    return chunks
