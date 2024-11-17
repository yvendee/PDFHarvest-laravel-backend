# syntax=docker.io/docker/dockerfile:1.6
FROM python:3.11-slim-bullseye

ARG FLASK_APP
ARG FLASK_ENV
ARG FLASK_DEBUG
ENV PYHTONUNBUFFERED=1
ENV FLASK_APP=${FLASK_APP:-app.py}
ENV FLASK_ENV=${FLASK_ENV:-development}
ENV FLASK_DEBUG=${FLASK_DEBUG:-1}

WORKDIR /app

COPY --link requirements.txt requirements.txt

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get --no-install-recommends install -y \
    # ffmpeg \
    libreoffice \
    tesseract-ocr \
    tesseract-ocr-eng \
    # poppler-utils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install -r requirements.txt

# Set permissions for /tmp directory
RUN chmod -R 755 /tmp

COPY --link ./ /app/

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]