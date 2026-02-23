FROM python:3.11-slim
WORKDIR /app

COPY servers/admin_server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY servers/admin_server/ /app/

EXPOSE 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]