FROM python:3.11-slim

# Install system dependencies for WeasyPrint and PostgreSQL
RUN apt-get update && apt-get install -y \
    # PostgreSQL client libraries for psycopg2
    libpq-dev \
    gcc \
    # WeasyPrint runtime dependencies
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    # WeasyPrint additional dependencies
    libxml2 \
    libxslt1.1 \
    libharfbuzz0b \
    libfribidi0 \
    libpng16-16 \
    libjpeg62-turbo \
    libopenjp2-7 \
    # Font support
    fonts-dejavu-core \
    fontconfig \
    # Clean up
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements files
COPY requirements.txt streamlit-requirements.txt analysis-requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r streamlit-requirements.txt && \
    pip install --no-cache-dir -r analysis-requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Start command with visible logging (let crashes be seen in Railway logs)
CMD ["sh", "-c", "echo 'Starting app...' && streamlit run home.py --server.port ${PORT:-5000} --server.address 0.0.0.0 --server.headless true 2>&1 | tee /tmp/app.log"]