FROM python:3.9-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y \
    clang \
    lld \
    git \
    curl \
    wget \
    wabt \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    rustup target add wasm32-unknown-unknown
    
RUN wget https://github.com/tinygo-org/tinygo/releases/download/v0.33.0/tinygo_0.33.0_amd64.deb && \
    dpkg -i tinygo_0.33.0_amd64.deb && \
    rm tinygo_0.33.0_amd64.deb

RUN npm install -g assemblyscript

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]
