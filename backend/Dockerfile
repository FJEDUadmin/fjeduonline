FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY src /app/src

RUN pip install --no-cache-dir -e .

COPY data /app/data
COPY r_modules /app/r_modules

EXPOSE 8000

CMD ["uvicorn", "adductomics_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
