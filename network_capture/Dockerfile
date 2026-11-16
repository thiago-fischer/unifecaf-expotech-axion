FROM debian:12.12-slim@sha256:d5d3f9c23164ea16f31852f95bd5959aad1c5e854332fe00f7b3a20fcc9f635c

ARG TSHARK_VERSION=4.0.17-0+deb12u3
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 HOME=/tmp

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        libcap2-bin \
        python3 \
        tshark=${TSHARK_VERSION} \
        util-linux \
    && setcap cap_net_raw,cap_net_admin=eip /usr/bin/dumpcap \
    && tshark --version | head -n 1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10002 capture

WORKDIR /app
COPY network_capture/collector.py /app/collector.py

ENTRYPOINT ["setpriv", "--reuid=10002", "--regid=10002", "--clear-groups", "--inh-caps=+net_admin,+net_raw", "--ambient-caps=+net_admin,+net_raw", "--bounding-set=-setuid,-setgid,-setpcap", "python3", "/app/collector.py"]
