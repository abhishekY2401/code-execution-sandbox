FROM python:3.12-slim

WORKDIR /sandbox

# create writable temp dirs
RUN mkdir -p /tmp /var/tmp /usr/tmp /sandbox/tmp \
    && chmod 1777 /tmp /var/tmp /usr/tmp \
    && chmod 777 /sandbox/tmp

COPY batch_run_code.py /sandbox/batch_run_code.py

CMD ["python", "/sandbox/batch_run_code.py"]