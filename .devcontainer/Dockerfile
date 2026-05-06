# Dev Container für scriptility.
# Liefert die in docs/REQUIREMENTS.md aufgeführten Pflicht- und empfohlenen Tools.
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

ARG TARGETARCH=amd64
ARG TASK_VERSION=v3.39.2
ARG TERRAFORM_VERSION=1.9.8
ARG GITLEAKS_VERSION=8.21.2
ARG STACKIT_VERSION=0.21.1

ENV DEBIAN_FRONTEND=noninteractive

# Pflicht- und Hilfstools per apt (bash >= 5 ist im Base-Image).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bats \
        shellcheck \
        jq \
        dnsutils \
        openssh-client \
        unzip \
        ca-certificates \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# uv (Python-Paketmanager) — systemweit, damit alle Shells es finden.
RUN curl -LsSf https://astral.sh/uv/install.sh \
        | env UV_INSTALL_DIR=/usr/local/bin UV_UNMANAGED_INSTALL=1 sh

# Task (Entry Point für sämtliche Skripte).
RUN curl -fsSL "https://github.com/go-task/task/releases/download/${TASK_VERSION}/task_linux_${TARGETARCH}.tar.gz" \
        | tar -xz -C /usr/local/bin task

# Terraform.
RUN curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${TARGETARCH}.zip" \
        -o /tmp/terraform.zip \
    && unzip -q /tmp/terraform.zip -d /usr/local/bin \
    && rm /tmp/terraform.zip

# gitleaks (Secret-Scan im pre-commit).
RUN GLARCH="$([ "${TARGETARCH}" = "amd64" ] && echo x64 || echo "${TARGETARCH}")" \
    && curl -fsSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_${GLARCH}.tar.gz" \
        | tar -xz -C /usr/local/bin gitleaks

# STACKIT-CLI — best effort; bricht den Build nicht ab, falls das Asset nicht existiert.
RUN curl -fsSL "https://github.com/stackitcloud/stackit-cli/releases/download/v${STACKIT_VERSION}/stackit_${STACKIT_VERSION}_linux_${TARGETARCH}.tar.gz" \
        -o /tmp/stackit.tar.gz \
    && tar -xzf /tmp/stackit.tar.gz -C /usr/local/bin stackit \
    && rm /tmp/stackit.tar.gz \
    || echo "WARN: stackit-cli konnte nicht installiert werden — siehe docs/REQUIREMENTS.md"

USER vscode
