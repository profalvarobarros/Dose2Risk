import sys
import os

def read_docx_fallback(path):
    import zipfile
    import xml.etree.ElementTree as ET
    
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    text_content = []
    
    try:
        with zipfile.ZipFile(path) as docx:
            xml_content = docx.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            
            for p in tree.iter(f"{{{ns['w']}}}p"):
                texts = [node.text for node in p.iter(f"{{{ns['w']}}}t") if node.text]
                if texts:
                    text_content.append(''.join(texts))
    except Exception as e:
        return f"Error reading docx with fallback: {e}"
        
    return '\n'.join(text_content)

def read_docx_lib(path):
    import docx
    doc = docx.Document(path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python _read_docx.py <input_docx> <output_txt>")
        sys.exit(1)
        
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    content = ""
    try:
        content = read_docx_lib(input_path)
    except ImportError:
        content = read_docx_fallback(input_path)
    except Exception as e:
        content = f"Error: {e}"
        
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
