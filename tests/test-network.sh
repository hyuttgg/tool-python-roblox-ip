#!/usr/bin/env bash
# ==============================================================================
# TEST NETWORK & DNS
# ==============================================================================
source "$(dirname "$0")/../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Kiểm tra module DNS Resolver..."
$PYTHON_CMD -c "from network.dns import DNSResolver; s = DNSResolver.test_dns_server('8.8.8.8'); assert s > 0; print('[PASS] DNS Resolver Test OK')"
