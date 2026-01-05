# Multi-stage build para segurança e tamanho reduzido
FROM python:3.9-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Imagem Final ---
FROM python:3.9-slim

WORKDIR /app

# Copiar bibliotecas do builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copiar código fonte
COPY . .

# Criar usuário não-root por segurança
RUN useradd -m doseuser && chown -R doseuser /app
USER doseuser

# Portas e Variáveis
EXPOSE 5000
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# Comando de entrada (Gunicorn para produção)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "dose2risk.api:create_app()"]
