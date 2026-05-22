use anyhow::Result;
use std::path::Path;

/// Run Tesseract on an image file and return the extracted text.
/// Requires `tesseract` binary on PATH.
/// Language set: eng + tha + chi_sim + vie + ind — tuned for SEA legal documents.
pub async fn ocr(image_path: &Path) -> Result<String> {
    let output = tokio::process::Command::new("tesseract")
        .arg(image_path)
        .arg("stdout")
        .args(["-l", "eng+tha+chi_sim+vie+ind"])
        .args(["--psm", "3"])
        .output()
        .await
        .map_err(|_| anyhow::anyhow!(
            "tesseract not found. Install: apt install tesseract-ocr tesseract-ocr-tha \
             tesseract-ocr-chi-sim tesseract-ocr-vie tesseract-ocr-ind"
        ))?;

    if !output.status.success() {
        anyhow::bail!("tesseract failed: {}", String::from_utf8_lossy(&output.stderr));
    }

    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}
