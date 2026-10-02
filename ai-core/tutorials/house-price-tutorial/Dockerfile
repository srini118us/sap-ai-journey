FROM python:3.11-slim

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

RUN mkdir -p /app/src && \
    mkdir -p /tmp/sklearn_data && \
    chmod -R 777 /tmp/sklearn_data

COPY main.py /app/src/main.py

RUN chgrp -R nogroup /app && \
    chmod -R 770 /app

ENV SCIKIT_LEARN_DATA=/tmp/sklearn_data
ENV HOME=/tmp
