FROM rust:1.88-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY Cargo.toml Cargo.lock* ./
COPY src ./src

RUN cargo build --release

# ── Runtime image ─────────────────────────────────────────────────────────────
FROM debian:bookworm-slim

# System deps: poppler-utils (pdftoppm for PDF→PNG) + Tesseract + SEA language packs
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-tha \
    tesseract-ocr-chi-sim \
    tesseract-ocr-vie \
    tesseract-ocr-ind \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/target/release/extract-sidecar .

EXPOSE 4000

CMD ["./extract-sidecar"]
