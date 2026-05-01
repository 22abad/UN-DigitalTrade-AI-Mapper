# Folder logic: #
```
pdf-reader/ structure:
pdf-reader/
├── README.md                           # Strategy doc + pipeline diagram
├── requirements.txt                    # pymupdf, pdf2image, pytesseract, opencv, openai
├── main.py                             # Unified entry point — auto-routes by PDF type
├── non-ocr/
│   ├── __init__.py
│   └── pymupdf_extractor.py            # Path A: PyMuPDF direct text extraction
└── ocr-service/
    ├── __init__.py
    ├── tesseract_extractor.py           # Path B: pdf2pym → Tesseract → OpenAI fallback
    └── openai_fallback.py              # GPT-4o Vision when Tesseract fails
```