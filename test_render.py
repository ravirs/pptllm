import os
import subprocess
from pdf2image import convert_from_path

def export_to_thumbnails(pptx_path: str, output_dir: str):
    """
    Converts a PPTX file to a series of JPEG thumbnails using LibreOffice and pdf2image.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Convert PPTX to PDF using LibreOffice headless
    pdf_path = pptx_path.replace(".pptx", ".pdf")
    try:
        # Mac OS path for LibreOffice or using 'soffice' if linked
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", os.path.dirname(os.path.abspath(pptx_path)), pptx_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        print(f"LibreOffice conversion failed: {e.stderr.decode()}")
        return []
    except FileNotFoundError:
        print("LibreOffice (soffice) not found on path.")
        return []

    # 2. Convert PDF to Images
    if not os.path.exists(pdf_path):
        print("PDF was not created.")
        return []
        
    images = convert_from_path(pdf_path)
    output_files = []
    
    for i, image in enumerate(images):
        out_path = os.path.join(output_dir, f"slide_{i+1}.jpg")
        image.save(out_path, "JPEG")
        output_files.append(out_path)
        print(f"Saved {out_path}")
        
    return output_files

if __name__ == "__main__":
    if os.path.exists("sample_template.pptx"):
        export_to_thumbnails("sample_template.pptx", "test_thumbnails")
