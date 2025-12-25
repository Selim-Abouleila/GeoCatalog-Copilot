from bs4 import BeautifulSoup
import html
import re

def clean_html_to_text(html_content: str) -> str:
    """
    Converts raw HTML content to readable plain text.
    
    Cleaning steps:
    1. Handles None/empty input.
    2. Uses BeautifulSoup to strip tags.
    3. Unescapes HTML entities (e.g., &nbsp; -> space).
    4. Normalizes whitespace (removes excessive newlines/spaces).
    
    Args:
        html_content (str): The raw HTML string.
        
    Returns:
        str: Cleaned plain text safe for display.
    """
    if not html_content:
        return ""
        
    try:
        # 1. Parse HTML
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 2. Extract text (separator=' ' adds space between block elements)
        text = soup.get_text(separator=' ')
        
        # 3. Unescape entities (BS4 usually handles this, but explicit unescape is safe)
        text = html.unescape(text)
        
        # 4. Normalize whitespace
        # Replace multiple spaces/newlines with single space/appropriate breaks if needed.
        # For description text, we often want to preserve some paragraph structure if possible,
        # but standard get_text() with separator is usually "flat". 
        # Here we'll just collapse excessive whitespace to make it clean.
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    except Exception as e:
        # Fallback if BS4 fails (rare)
        return str(html_content)
