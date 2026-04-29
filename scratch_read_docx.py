import sys
try:
    from docx import Document
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx"])
    from docx import Document

doc_path = r"e:\be_mpr\report\be_report (1).docx"
out_path = r"e:\be_mpr\report_dump.txt"

try:
    doc = Document(doc_path)
    with open(out_path, 'w', encoding='utf-8') as f:
        for i, para in enumerate(doc.paragraphs):
            if para.text.strip():
                f.write(f"[{i}] {para.text}\n")
    print(f"Successfully dumped to {out_path}")
except Exception as e:
    print(f"Error: {e}")
