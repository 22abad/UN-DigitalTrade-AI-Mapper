use anyhow::{Context, Result};
use std::path::Path;

/// Run Tesseract OCR on a single image file via CLI subprocess.
pub async fn ocr(image_path: &Path) -> Result<String> {
    let output = tokio::process::Command::new("tesseract")
        .arg(image_path.as_os_str())
        .arg("stdout")
        .arg("-l")
        .arg("eng")
        .arg("--psm")
        .arg("3") // fully automatic page segmentation
        .output()
        .await
        .context("Failed to run tesseract. Is it installed? (brew install tesseract)")?;

    if !output.status.success() {
        anyhow::bail!(
            "Tesseract failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}
