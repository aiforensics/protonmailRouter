FROM debian
RUN apt update && \
    apt install curl libglx0 libopengl0 libgl1 libxkbcommon0 libfontconfig1 python3 python3-pip -y && \
    curl -o proton_bridge.deb https://proton.me/download/bridge/protonmail-bridge_3.1.2-1_amd64.deb && \
    apt install -y ./proton_bridge.deb && \
    