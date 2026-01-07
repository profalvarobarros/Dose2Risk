# Multi-stage build
FROM python:3.9-slim as builder
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- Imagem Final ---
FROM python:3.9-slim
WORKDIR /app

# Copiar libs instaladas para o local padrão do Python
COPY --from=builder /install /usr/local

# Copiar código fonte
COPY . .

# Criar usuário não-root
RUN useradd -m doseuser && chown -R doseuser /app
USER doseuser

EXPOSE 5000
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "dose2risk.api:create_app()"]
