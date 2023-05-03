FROM debian
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install curl python3 python3-pip -y && \
    useradd -m aifuser && \
    curl -o proton_bridge.deb https://proton.me/download/bridge/protonmail-bridge_3.1.2-1_amd64.deb && \
    apt-get install -y ./proton_bridge.deb && \
    rm proton_bridge.deb
USER aifuser
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt --user
CMD python3 -u main.py

LABEL org.opencontainers.image.source = "https://github.com/aiforensics/protonmailRouter"