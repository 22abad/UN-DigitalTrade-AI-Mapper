pub mod openai_vision;
pub mod tesseract;

use anyhow::Result;
use std::path::{Path, PathBuf};

/// Which OCR engine to use — controlled by `OCR_MODE` env var.
/// "tesseract" | "openai" | "auto" (default: auto)
#[derive(Debug, Clone, Copy)]
pub enum OcrMode {
    Tesseract,
    OpenAI,
    Auto,
}

impl OcrMode {
    pub fn from_env() -> Self {
        match std::env::var("OCR_MODE")
            .unwrap_or_default()
            .to_lowercase()
            .as_str()
        {
            "tesseract"          => OcrMode::Tesseract,
            "openai" | "vision"  => OcrMode::OpenAI,
            _                    => OcrMode::Auto,
        }
    }
}

/// Extract text from a PDF or image file.
/// Returns (full_text, provider_name).
///
/// PDFs are rasterised with pdftoppm (poppler) at 300 DPI before OCR.
/// All pages run concurrently; results are joined with \n\n.
pub async fn extract_text_with_provider(file_path: &Path) -> Result<(String, &'static str)> {
    let mode = OcrMode::from_env();

    let image_paths = if is_pdf(file_path) {
        pdf_to_images(file_path).await?
    } else {
        vec![file_path.to_path_buf()]
    };

    let handles: Vec<_> = image_paths
        .into_iter()
        .enumerate()
        .map(|(i, img)| {
            tokio::spawn(async move {
                tracing::debug!("OCR page {} ({:?})", i + 1, mode);
                let result: Result<(String, &'static str)> = match mode {
                    OcrMode::Tesseract => {
                        let t = tesseract::ocr(&img).await?;
                        Ok((t, "tesseract"))
                    }
                    OcrMode::OpenAI => {
                        let t = openai_vision::ocr(&img).await?;
                        Ok((t, "openai_vision"))
                    }
                    OcrMode::Auto => {
                        match tesseract::ocr(&img).await {
                            Ok(t) if t.trim().len() > 50 => Ok((t, "tesseract")),
                            Ok(_) | Err(_) => {
                                tracing::debug!("Tesseract insufficient, falling back to OpenAI Vision");
                                let t = openai_vision::ocr(&img).await?;
                                Ok((t, "openai_vision"))
                            }
                        }
                    }
                };
                result
            })
        })
        .collect();

    let mut all_text = String::new();
    let mut provider_used = "unknown";

    for handle in handles {
        let (text, provider) = handle.await??;
        provider_used = provider;
        all_text.push_str(text.trim_end());
        all_text.push_str("\n\n");
    }

    Ok((all_text, provider_used))
}

fn is_pdf(path: &Path) -> bool {
    path.extension().and_then(|e| e.to_str()) == Some("pdf")
}

/// Rasterise every PDF page to PNG at 300 DPI using pdftoppm (poppler-utils).
async fn pdf_to_images(pdf_path: &Path) -> Result<Vec<PathBuf>> {
    let tmp_dir = std::env::temp_dir()
        .join(format!("sidecar_ocr_{}", uuid::Uuid::new_v4()));
    tokio::fs::create_dir_all(&tmp_dir).await?;

    let prefix = tmp_dir.join("page");
    let output = tokio::process::Command::new("pdftoppm")
        .args(["-png", "-r", "300"])
        .arg(pdf_path)
        .arg(&prefix)
        .output()
        .await
        .map_err(|_| anyhow::anyhow!(
            "pdftoppm not found. Install poppler-utils: apt install poppler-utils"
        ))?;

    if !output.status.success() {
        anyhow::bail!("pdftoppm failed: {}", String::from_utf8_lossy(&output.stderr));
    }

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
