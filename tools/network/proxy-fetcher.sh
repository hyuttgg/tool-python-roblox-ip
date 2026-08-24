#!/usr/bin/env bash
# ==============================================================================
# PROXY SCRAPER & SCRAPESTACK CLIENT
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

COUNTRY="${1:-MULTI}"
log_info "Cào danh sách Proxy theo quốc gia: $COUNTRY..."
$PYTHON_CMD -c "from network.proxy_fetcher import ProxyFetcher; proxies = ProxyFetcher.get_proxies_batch(5, '$COUNTRY'); [print(f'-> IP: {p[\"ip\"]} | Region: {p[\"region\"]}') for p in proxies]"
