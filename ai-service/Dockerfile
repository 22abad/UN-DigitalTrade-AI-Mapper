FROM python:3.11-slim
# 3.11 matches the Python version requirements.txt was pip-compile'd
# against. If you change the Python version here, also regenerate the
# lockfile via `cd ai-service && pip-compile requirements.in -o requirements.txt`
# under that same Python version, otherwise the pins may not be installable.

WORKDIR /app

# Install system dependencies for Playwright, PDF extraction (Poppler), and OCR (Tesseract)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    # Playwright dependencies
    libnss3 \
    libnspr4 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrender1 \
    libxtst6 \
    libcups2 \
    libxss1 \
    libxrandr2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    libxkbcommon0 \
    libdrm2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
# Install Playwright browsers
RUN playwright install chromium

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
