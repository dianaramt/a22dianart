# Imaxe da aplicación Django de Bambi (úsase desde compose.yaml)
FROM python:3.13-slim

# Sen ficheiros .pyc e coa saída de Python directa nos logs do contedor
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Primeiro só as dependencias: Docker reutiliza esta capa mentres requirements.txt non cambie
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
