#!/usr/bin/env bash
set -euo pipefail

domain="${1:?domain is required}"
cert_root="${CERT_ROOT:-/opt/acme-cert-manager/certs}"
secret_file="${PROVIDER_ENV_FILE:-/opt/acme-cert-manager/secrets/provider.env}"
deployer="${QINIU_DEPLOYER:-/opt/acme-cert-manager/bin/qiniu-cert-deploy.py}"
base="${cert_root}/${domain}"

if [[ ! -s "${base}/fullchain.pem" || ! -s "${base}/privkey.pem" ]]; then
  echo "certificate files are missing for ${domain}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
. "${secret_file}"
set +a

exec /usr/bin/python3 \
  "${deployer}" \
  "${domain}" "${base}/fullchain.pem" "${base}/privkey.pem"
