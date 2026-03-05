FROM python:3.12-slim

WORKDIR /app

#install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#copy the rest of the application code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0", "--port", "8000"]
