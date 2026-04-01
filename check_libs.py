
try:
    import pypdf
    print("pypdf: OK")
except ImportError:
    print("pypdf: MISSING")

try:
    import docx
    print("docx: OK")
except ImportError:
    print("docx: MISSING")

try:
    import pandas
    print("pandas: OK")
except ImportError:
    print("pandas: MISSING")

try:
    import openpyxl
    print("openpyxl: OK")
except ImportError:
    print("openpyxl: MISSING")
