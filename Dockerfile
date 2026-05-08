FROM python:3.12-slim

WORKDIR /eticket_project

# =========================================
# System dependencies (IMPORTANT FOR WEASYPRINT)
# =========================================
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    python3-dev \
    pkg-config \
    libcairo2 \
    libcairo2-dev \
    pango1.0-tools \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu-core \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# =========================================
# Python dependencies
# =========================================
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =========================================
# Copy project
# =========================================
COPY . .

# =========================================
# Static files (optional safe)
# =========================================
RUN mkdir -p staticfiles
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# =========================================
# Run with Gunicorn (correct for production)
# =========================================
CMD ["gunicorn", "eticket_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]