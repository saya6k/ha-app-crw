# BUILD_FROM is no longer injected by the Supervisor (>=2026.04.0) — default to
# the multi-arch HA base manifest, pinned to an Alpine version tag instead of
# the moving :latest. Overridable with --build-arg.
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ---- crw-server (prebuilt static binary, AGPL-3.0) -----------------------
ARG CRW_VERSION=0.25.1
ARG CRW_SHA256_AMD64=70484626341003e784bcc04b5d7552ba189091377c9a6b872bde499bf85470c9
ARG CRW_SHA256_AARCH64=0dae0a2b0c7db5f2f4daab12c4350c48d6b5b115e993853468d55877a5433786

RUN set -eu; \
    case "$(uname -m)" in \
      x86_64)  asset="crw-server-linux-x64.tar.gz";   sha="${CRW_SHA256_AMD64}" ;; \
      aarch64) asset="crw-server-linux-arm64.tar.gz"; sha="${CRW_SHA256_AARCH64}" ;; \
      *) echo "unsupported architecture: $(uname -m)" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/crw.tar.gz \
      "https://github.com/us/crw/releases/download/v${CRW_VERSION}/${asset}"; \
    echo "${sha}  /tmp/crw.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/crw.tar.gz -C /usr/local/bin crw-server; \
    chmod a+x /usr/local/bin/crw-server; \
    rm /tmp/crw.tar.gz

# ---- MCP bridge (Python venv) ---------------------------------------------
COPY rootfs/opt/mcp-bridge/requirements.txt /tmp/requirements.txt
RUN apk add --no-cache python3 py3-pip \
 && python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt \
 && rm /tmp/requirements.txt

# ---- rootfs (s6 services) -------------------------------------------------
COPY rootfs /

RUN find /etc/s6-overlay/s6-rc.d -type f \( -name run -o -name finish \) -exec chmod a+x {} \; \
 && find /etc/s6-overlay/s6-rc.d -type f -name type -exec chmod 644 {} \;

WORKDIR /
