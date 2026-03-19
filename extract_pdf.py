import PyPDF2
import sys

sys.stdout.reconfigure(encoding='utf-8')
reader = PyPDF2.PdfReader('GeoDispatch_Context_Aware_Doc.pdf')
with open('doc.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(page.extract_text() for page in reader.pages))
