FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y build-essential libffi-dev \
    && pip install --no-cache-dir --upgrade pip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-u", "main.py"]
