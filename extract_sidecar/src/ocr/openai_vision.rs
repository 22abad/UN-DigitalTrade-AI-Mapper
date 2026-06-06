use anyhow::{Context, Result};
use base64::{engine::general_purpose::STANDARD as B64, Engine};
use serde_json::json;
use std::path::Path;

/// Send an image to OpenAI GPT-4o for OCR.
/// Falls back to this when Tesseract returns < 50 chars (scanned / complex layout).
/// Requires OPENAI_API_KEY in environment.
pub async fn ocr(image_path: &Path) -> Result<String> {
    let api_key = std::env::var("OPENAI_API_KEY")
        .context("OPENAI_API_KEY not set — cannot use OpenAI Vision fallback")?;

    let bytes = tokio::fs::read(image_path).await?;
    let b64   = B64.encode(&bytes);
    let mime  = if image_path.extension().and_then(|e| e.to_str()) == Some("png") {
        "image/png"
    } else {
        "image/jpeg"
    };

    let client = reqwest::Client::new();
    let body = json!({
        "model": "gpt-4o",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Extract all text from this document image. Preserve paragraph structure. Return only the extracted text."
                },
                {
                    "type": "image_url",
                    "image_url": { "url": format!("data:{mime};base64,{b64}") }
                }
            ]
        }],
        "max_tokens": 4096
    });

    let resp: serde_json::Value = client
        .post("https://api.openai.com/v1/chat/completions")
        .bearer_auth(api_key)
        .json(&body)
        .send()
        .await?
        .json()
        .await?;

    let text = resp["choices"][0]["message"]["content"]
        .as_str()
        .unwrap_or("")
        .to_string();

    Ok(text)
}
