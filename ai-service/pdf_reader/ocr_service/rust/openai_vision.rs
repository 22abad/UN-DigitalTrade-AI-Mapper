use anyhow::{Context, Result};
use base64::Engine;
use std::path::Path;

/// Send image to OpenAI GPT-4o vision endpoint for OCR.
pub async fn ocr(image_path: &Path) -> Result<String> {
    let api_key =
        std::env::var("OPENAI_API_KEY").context("OPENAI_API_KEY required for Vision OCR")?;

    let image_bytes = tokio::fs::read(image_path).await?;
    let b64 = base64::engine::general_purpose::STANDARD.encode(&image_bytes);

    let mime = match image_path.extension().and_then(|e| e.to_str()) {
        Some("png") => "image/png",
        Some("jpg") | Some("jpeg") => "image/jpeg",
        _ => "image/png",
    };

    let client = reqwest::Client::new();
    let body = serde_json::json!({
        "model": "gpt-4o",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Extract all text from this document image. Preserve paragraph structure with blank lines between sections. Return only the extracted text, no commentary."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": format!("data:{};base64,{}", mime, b64)
                    }
                }
            ]
        }],
        "max_tokens": 4096
    });

    let resp = client
        .post("https://api.openai.com/v1/chat/completions")
        .bearer_auth(&api_key)
        .json(&body)
        .send()
        .await?
        .json::<serde_json::Value>()
        .await?;

    if let Some(err) = resp.get("error") {
        anyhow::bail!("OpenAI Vision error: {}", err);
    }

    let text = resp["choices"][0]["message"]["content"]
        .as_str()
        .unwrap_or("")
        .to_string();

    Ok(text)
}
