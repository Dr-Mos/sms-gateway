FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gammu \
        libgammu-dev \
        usbutils \
    && rm -rf /var/lib/apt/lists/* && \
    apt-get clean

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ templates/

VOLUME ["/data"]

ENV TTY_SMS=/dev/ttyUSB1 \
    TTY_AT="" \
    POLL_INTERVAL=3 \
    PASSWORD=admin \
    MODEM_PHONE="" \
    SECRET_KEY=""

EXPOSE 5000

CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:5000", "app:app"]
