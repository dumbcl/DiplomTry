FROM python:3.11
WORKDIR /code
COPY requirements.txt .
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean
RUN pip install --no-cache-dir -r requirements.txt
COPY . .