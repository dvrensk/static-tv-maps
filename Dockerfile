FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The container runs as the invoking host user (no HOME), so give matplotlib
# a writable config/cache dir instead of letting it probe /.config.
ENV MPLCONFIGDIR=/tmp/matplotlib

# Stdout has no TTY under `docker run`, so Python would block-buffer it and
# the tuner's request log (and render progress) would only appear on exit.
ENV PYTHONUNBUFFERED=1

# The interactive label tuner (make tune) listens here.
EXPOSE 8321

CMD ["python", "generate.py", "all"]
