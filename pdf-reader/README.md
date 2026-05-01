# PDF Reading Strategy

## Pipeline Overview

```
┌──────────────────────────────────────────────────────────┐
│                    Upload / Download                      │
│                        PDF                                │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │  PDF Type Detection     │
              │  (is_scanned?)          │
              └───────────┬─────────────┘
                          │
            ┌─────────────┴─────────────┐
            │                           │
            ▼                           ▼
    ┌──────────────┐            ┌──────────────────┐
    │ Pure Text PDF│            │ Scanned / Hybrid │
    │   (fast)     │            │   (image-based)  │
    └──────┬───────┘            └────────┬─────────┘
           │                             │
           ▼                             ▼
    ┌──────────────┐            ┌──────────────────┐
    │ PyMuPDF      │            │ pdf2pym (300dpi) │
    │ .get_text()  │            │ → PNG images     │
    └──────┬───────┘            └────────┬─────────┘
           │                             │
           │                      ┌──────▼───────┐
           │                      │ Tesseract OCR│
           │                      │ --psm 3 -l   │
           │                      └──────┬───────┘
           │                             │
           ▼                             ▼
    ┌─────────────────────────────────────────┐
    │           Merge & Clean Text            │
    │  (section splitting, dedup, normalize)  │
    └─────────────────────────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │  Store in DB            │
              │  document_sections      │
              └─────────────────────────┘
```

## Decision Logic: Is a PDF Scanned?

A PDF is classified as "scanned" when:
1. **No text layer** — PyMuPDF returns empty or <50 chars from first page
2. **Image-heavy** — pages contain large images with minimal text objects

## Path A: Pure Text PDF (PyMuPDF)

- Uses PyMuPDF (`fitz`) to extract text layer directly
- Fast, no image processing needed
- Preserves document structure (headings, paragraphs)

## Path B: Scanned/Hybrid PDF (pdf2pym + Tesseract)

- Renders each page to a 300 DPI PNG image
- Runs Tesseract OCR with PSM 3 (full auto segmentation)
- Falls back to OpenAI Vision if Tesseract returns insufficient text

## Dependencies

| Package | Purpose |
|---|---|
| `pymupdf` (fitz) | Pure text extraction + page rendering |
| `pytesseract` | Python wrapper for Tesseract OCR |
| `pdf2image` | pdf2pym wrapper (uses poppler) |
| `opencv-python` | Image preprocessing for better OCR |
