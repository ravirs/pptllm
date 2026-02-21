import os
import tempfile

def save_uploaded_file(uploaded_file) -> str:
    """Save Streamlit uploaded file to a temporary file, return the path."""
    # We use NamedTemporaryFile to ensure PPTX can read it from a path
    try:
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            return tmp.name
    except Exception as e:
        return ""
