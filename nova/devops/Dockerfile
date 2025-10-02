FROM python:3.11-slim

WORKDIR /app

# Installer systempakker
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc make g++ git && \
    rm -rf /var/lib/apt/lists/*

# Kopier prosjekt
COPY . /app

# Installer Python-avhengigheter
RUN pip install --no-cache-dir -r requirements.txt || true

ENV NOVA_HOME=/tmp/nova_home/nova
RUN mkdir -p $NOVA_HOME/logs $NOVA_HOME/data

ENTRYPOINT ["python", "-m", "nova.engine.run"]
