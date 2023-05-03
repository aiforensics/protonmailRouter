FROM alpine
RUN apk add --no-cache dpkg curl python3 py3-pip mesa-gl libc6-compat libsecret glib-dev libstdc++6 libgcc ttf-dejavu gcompat && \
    adduser -D aifuser && \
    curl -o proton_bridge.deb https://proton.me/download/bridge/protonmail-bridge_3.1.2-1_amd64.deb && \
    dpkg --add-architecture amd64 && \
    dpkg -i --force-depends ./proton_bridge.deb && \
    rm proton_bridge.deb
USER aifuser
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt --user
CMD python3 main.py

# Also tried: https://github.com/sgerrand/alpine-pkg-glibc