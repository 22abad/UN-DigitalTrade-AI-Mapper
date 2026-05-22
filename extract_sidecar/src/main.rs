mod ocr;

use anyhow::{Context, Result};
use axum::{
    extract::{Multipart, State},
    http::{HeaderValue, StatusCode},
    routing::post,
    Json, Router,
};
use chrono::{DateTime, Duration, Utc};
use hex::encode as hex_encode;
use serde::Serialize;
use sha2::{Digest, Sha256};
use sqlx::{postgres::PgPoolOptions, FromRow, PgPool};
use std::path::Path;
use tower_http::cors::{AllowHeaders, AllowMethods, AllowOrigin, CorsLayer};
use uuid::Uuid;

// ── App state ─────────────────────────────────────────────────────────────────

#[derive(Clone)]
struct AppState {
    db:      PgPool,
    api_key: String,
}

// ── Auth middleware ───────────────────────────────────────────────────────────

async fn require_api_key(
    State(state): State<AppState>,
    request: axum::extract::Request,
    next: axum::middleware::Next,
) -> Result<axum::response::Response, StatusCode> {
    let token = request
        .headers()
        .get("Authorization")
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.strip_prefix("Bearer "));
    match token {
        Some(t) if t == state.api_key => Ok(next.run(request).await),
        _ => Err(StatusCode::UNAUTHORIZED),
    }
}

// ── Response / DB types ───────────────────────────────────────────────────────

#[derive(Serialize)]
struct ExtractTextResponse {
    /// Stable document ID — pass to FastAPI to reference the source doc.
    doc_id:       String,
    filename:     String,
    /// Full extracted text, all pages joined with \n\n.
    text:         String,
    /// true = served from DB cache; false = freshly OCR'd.
    cache_hit:    bool,
    /// "tesseract" | "openai_vision" | "none" (plain-text files)
    ocr_provider: String,
}

#[derive(FromRow)]
struct CachedDoc {
    id:             String,
    extracted_text: String,
    ocr_provider:   String,
    filename:       String,
}

fn err(status: StatusCode, msg: impl Into<String>) -> (StatusCode, Json<serde_json::Value>) {
    (status, Json(serde_json::json!({ "error": msg.into() })))
}

// ── Format classifier ─────────────────────────────────────────────────────────

fn classify_format(filename: &str) -> &'static str {
    match Path::new(filename)
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_lowercase()
        .as_str()
    {
        "pdf" | "jpg" | "jpeg" | "png" => "ocr",
        "txt" | "md"                   => "text",
        _                              => "unsupported",
    }
}

// ── Handler ───────────────────────────────────────────────────────────────────

/// POST /extract-text
///
/// Multipart fields:
///   file            — document to extract (pdf, jpg, jpeg, png, txt, md)
///   expires_in_days — optional TTL integer; omit for permanent storage
///
/// Flow:
///   1. SHA-256 hash the raw bytes.
///   2. Check extracted_documents for a non-expired hit → return immediately.
///   3. Miss: write tempfile → OCR → store result.
///   4. Return { doc_id, text, cache_hit, ocr_provider, filename }.
async fn extract_text_handler(
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Json<ExtractTextResponse>, (StatusCode, Json<serde_json::Value>)> {
    let mut file_data: Option<(String, Vec<u8>)> = None;
    let mut expires_in_days: Option<i64> = None;

    while let Some(field) = multipart
        .next_field()
        .await
        .map_err(|e| err(StatusCode::BAD_REQUEST, e.to_string()))?
    {
        match field.name() {
            Some("expires_in_days") => {
                let s = field.text().await
                    .map_err(|e| err(StatusCode::BAD_REQUEST, e.to_string()))?;
                expires_in_days = s.trim().parse::<i64>().ok();
            }
            _ => {
                let filename = field.file_name().unwrap_or("upload").to_string();
                let bytes = field.bytes().await
                    .map_err(|e| err(StatusCode::BAD_REQUEST, e.to_string()))?
                    .to_vec();
                file_data = Some((filename, bytes));
            }
        }
    }

    let (filename, bytes) = file_data
        .ok_or_else(|| err(StatusCode::BAD_REQUEST, "No file uploaded"))?;

    let fmt = classify_format(&filename);
    if fmt == "unsupported" {
        let ext = Path::new(&filename).extension()
            .and_then(|e| e.to_str()).unwrap_or("(none)");
        return Err(err(
            StatusCode::BAD_REQUEST,
            format!("Unsupported file type '.{ext}'. Accepted: pdf, jpg, jpeg, png, txt, md."),
        ));
    }

    // --- 1. Hash ---
    let hash = hex_encode(Sha256::digest(&bytes));

    // --- 2. Cache check ---
    let cached = sqlx::query_as::<_, CachedDoc>(
        r#"
        SELECT id, extracted_text, ocr_provider, filename
        FROM   extracted_documents
        WHERE  content_hash = $1
          AND  (expires_at IS NULL OR expires_at > NOW())
        LIMIT  1
        "#,
    )
    .bind(&hash)
    .fetch_optional(&state.db)
    .await
    .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    if let Some(doc) = cached {
        return Ok(Json(ExtractTextResponse {
            doc_id:       doc.id,
            filename:     doc.filename,
            text:         doc.extracted_text,
            cache_hit:    true,
            ocr_provider: doc.ocr_provider,
        }));
    }

    // --- 3. Extract ---
    let (text, ocr_provider) = if fmt == "ocr" {
        let suffix = Path::new(&filename).extension()
            .and_then(|e| e.to_str())
            .map(|e| format!(".{e}"))
            .unwrap_or_default();

        // tempfile::NamedTempFile cleans up on drop — no manual unlink needed.
        let tmp = tempfile::Builder::new()
            .prefix("sidecar_")
            .suffix(&suffix)
            .tempfile()
            .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

        tokio::fs::write(tmp.path(), &bytes).await
            .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

        let (t, p) = ocr::extract_text_with_provider(tmp.path()).await
            .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, format!("OCR failed: {e:#}")))?;

        (t, p.to_string())
    } else {
        let t = String::from_utf8(bytes.clone())
            .unwrap_or_else(|_| String::from_utf8_lossy(&bytes).into_owned());
        (t, "none".to_string())
    };

    if text.trim().is_empty() {
        return Err(err(StatusCode::UNPROCESSABLE_ENTITY, "File produced no extractable text."));
    }

    // --- 4. Store ---
    let doc_id   = Uuid::new_v4().to_string();
    let src_type = Path::new(&filename).extension()
        .and_then(|e| e.to_str()).unwrap_or("unknown").to_string();
    let expires_at: Option<DateTime<Utc>> =
        expires_in_days.map(|d| Utc::now() + Duration::days(d));

    sqlx::query(
        r#"
        INSERT INTO extracted_documents
            (id, content_hash, filename, source_type, ocr_provider, extracted_text, expires_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (content_hash) DO NOTHING
        "#,
    )
    .bind(&doc_id).bind(&hash).bind(&filename)
    .bind(&src_type).bind(&ocr_provider).bind(&text).bind(expires_at)
    .execute(&state.db)
    .await
    .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    // Canonical id — may differ from doc_id if concurrent insert won the race.
    let actual_id = sqlx::query_scalar::<_, String>(
        "SELECT id FROM extracted_documents WHERE content_hash = $1",
    )
    .bind(&hash)
    .fetch_one(&state.db)
    .await
    .map_err(|e| err(StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    Ok(Json(ExtractTextResponse {
        doc_id:       actual_id,
        filename,
        text,
        cache_hit:    false,
        ocr_provider,
    }))
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "extract_sidecar=info".parse().unwrap()),
        )
        .init();

    dotenvy::dotenv().ok();

    let database_url = std::env::var("DATABASE_URL")
        .context("DATABASE_URL must be set")?;
    let api_key = std::env::var("SIDECAR_API_KEY")
        .context("SIDECAR_API_KEY must be set")?;
    let addr = std::env::var("SIDECAR_ADDR")
        .unwrap_or_else(|_| "0.0.0.0:4000".to_string());

    let db = PgPoolOptions::new()
        .max_connections(10)
        .connect(&database_url)
        .await
        .context("Failed to connect to database")?;

    let state = AppState { db, api_key };

    let cors = CorsLayer::new()
        .allow_origin(AllowOrigin::list([
            "http://localhost:8000".parse::<HeaderValue>().unwrap(),
        ]))
        .allow_methods(AllowMethods::any())
        .allow_headers(AllowHeaders::any());

    let protected = Router::new()
        .route("/extract-text", post(extract_text_handler))
        .layer(axum::extract::DefaultBodyLimit::max(50 * 1024 * 1024))
        .layer(axum::middleware::from_fn_with_state(
            state.clone(),
            require_api_key,
        ));

    let app = Router::new()
        .route("/health", axum::routing::get(|| async { "OK" }))
        .merge(protected)
        .layer(cors)
        .with_state(state);

    tracing::info!("extract-sidecar listening on http://{}", addr);
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}
