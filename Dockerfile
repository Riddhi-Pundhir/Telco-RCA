FROM node:20-alpine AS frontend

WORKDIR /frontend

COPY package.json package-lock.json vite.config.js tailwind.config.js postcss.config.js index.html ./
COPY src ./src

RUN npm ci
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY server/ ./server/
COPY inference.py .
COPY --from=frontend /frontend/app/static ./app/static

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
