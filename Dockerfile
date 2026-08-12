FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The interactive label tuner (make tune) listens here.
EXPOSE 8321

CMD ["python", "generate.py", "all"]
