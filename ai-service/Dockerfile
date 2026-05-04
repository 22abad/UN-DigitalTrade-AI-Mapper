FROM python:3.11-slim
# 3.11 matches the Python version requirements.txt was pip-compile'd
# against. If you change the Python version here, also regenerate the
# lockfile via `cd ai-service && pip-compile requirements.in -o requirements.txt`
# under that same Python version, otherwise the pins may not be installable.

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
