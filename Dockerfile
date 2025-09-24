FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONUNBUFFERED=1
CMD ["bash","-lc","set -a && source .env && set +a && ENGINE_ONCE=0 ENGINE_LOOP_SEC=30 EXCHANGE=binance MODE=paper python -m nova.engine.run"]
