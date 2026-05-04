pub mod openai_vision;
pub mod tesseract;

use anyhow::{Context, Result};
use std::path::{Path, PathBuf};

/// OCR mode, controlled by the `OCR_MODE` env var.
///  - "tesseract" — Tesseract only, never calls OpenAI Vision
///  - "openai"    — OpenAI Vision only, skip Tesseract
///  - "auto"      — Tesseract first, fall back to OpenAI Vision (default)
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum OcrMode {
    Tesseract,
    OpenAI,
    Auto,
}

impl OcrMode {
    pub fn from_env() -> Self {
        match std::env::var("OCR_MODE").unwrap_or_default().to_lowercase().as_str() {
            "tesseract" => OcrMode::Tesseract,
            "openai" | "vision" => OcrMode::OpenAI,
            _ => OcrMode::Auto,
        }
    }
}

/// Extract text from an image or PDF file.
/// OCR strategy is controlled by the `OCR_MODE` env var (tesseract | openai | auto).
pub async fn extract_text(file_path: &Path) -> Result<String> {
    let mode = OcrMode::from_env();
    println!("  OCR mode: {:?}", mode);

    let image_paths = if is_pdf(file_path) {
        pdf_to_images(file_path).await?
    } else {
        vec![file_path.to_path_buf()]
    };

    let mut all_text = String::new();
    for (i, img) in image_paths.iter().enumerate() {
        println!("  OCR page {}...", i + 1);
        let text = match mode {
            OcrMode::Tesseract => {
                let t = tesseract::ocr(img).await?;
                println!("    Tesseract: {} chars", t.len());
                t
            }
            OcrMode::OpenAI => {
                let t = openai_vision::ocr(img).await?;
                println!("    OpenAI Vision: {} chars", t.len());
                t
            }
            OcrMode::Auto => {
                match tesseract::ocr(img).await {
                    Ok(t) if t.trim().len() > 50 => {
                        println!("    Tesseract OK ({} chars)", t.len());
                        t
                    }
                    Ok(_) | Err(_) => {
                        println!("    Tesseract insufficient, trying OpenAI Vision...");
                        openai_vision::ocr(img).await?
                    }
                }
            }
        };
        all_text.push_str(&text);
        all_text.push('\n');
    }
    Ok(all_text)
}

fn is_pdf(path: &Path) -> bool {
    path.extension().and_then(|e| e.to_str()) == Some("pdf")
}

/// Convert PDF pages to temporary PNG images using `pdftoppm` (from poppler).
async fn pdf_to_images(pdf_path: &Path) -> Result<Vec<PathBuf>> {
    let tmp_dir = std::env::temp_dir().join(format!("rag_ocr_{}", uuid::Uuid::new_v4()));
    tokio::fs::create_dir_all(&tmp_dir).await?;

    let prefix = tmp_dir.join("page");
    let output = tokio::process::Command::new("pdftoppm")
        .arg("-png")
        .arg("-r")
        .arg("300") // 300 DPI for good OCR quality
        .arg(pdf_path.as_os_str())
        .arg(prefix.as_os_str())
        .output()
        .await
        .context("Failed to run pdftoppm. Is poppler installed? (brew install poppler)")?;

    if !output.status.success() {
        anyhow::bail!(
            "pdftoppm failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    // Collect generated page images, sorted by name
    let mut pages: Vec<PathBuf> = Vec::new();
    let mut entries = tokio::fs::read_dir(&tmp_dir).await?;
    while let Some(entry) = entries.next_entry().await? {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) == Some("png") {
            pages.push(path);
        }
    }
    pages.sort();
    Ok(pages)
}
