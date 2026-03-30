FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN pip install --upgrade pip

COPY servers/mcp_server/ /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8000

CMD ["python", "fastmcp_server.py"]