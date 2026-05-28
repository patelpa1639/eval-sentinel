#!/usr/bin/env bash
# Agent Engine build-time installation script.
#
# Eval Sentinel's Arize Phoenix MCP server is launched via `npx`, which needs
# Node.js. The Agent Engine runtime is a Python image, so we install Node here
# at image-build time (runs as root during the build). Referenced from
# deployment/deploy.py via build_options={"installation_scripts": [...]}.
set -euo pipefail

apt-get update
apt-get install -y curl ca-certificates

# NodeSource: install a modern Node.js (22.x) so `npx @arizeai/phoenix-mcp` runs.
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs

echo "node: $(node --version)"
echo "npx:  $(npx --version)"
