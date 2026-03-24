FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    r-base \
    build-essential \
    gfortran \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/pyproject.toml
COPY src /app/src

RUN pip install --no-cache-dir -e .

COPY data /app/data
COPY r_modules /app/r_modules

RUN Rscript /app/r_modules/install_packages.R \
    /app/r_modules/cran_packages.txt \
    /app/r_modules/bioc_packages.txt \
    /app/r_modules/packages

EXPOSE 8000

CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY:-2} -b 0.0.0.0:${PORT:-8000} adductomics_api.main:app"]
