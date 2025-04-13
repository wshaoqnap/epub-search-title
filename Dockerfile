# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安裝必要套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 確保相關的子目錄被包含
COPY default_notes default_notes
COPY up_notes up_notes
COPY cache cache
COPY modules modules
COPY titles titles
COPY app.py .
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
