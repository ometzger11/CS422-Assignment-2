FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Ubuntu 24.04 blocks pip into the system Python, so use a venv
COPY requirements.txt .
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt
ENV PATH=/opt/venv/bin:$PATH

COPY . .

# Results (CSVs, plots, environment.txt) are written here; mount a host folder on it
ENV RESULTS_DIR=/results
VOLUME /results

ENTRYPOINT ["./run_all.sh"]