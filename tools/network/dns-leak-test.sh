#!/usr/bin/env bash
# ==============================================================================
# DNS LEAK & RESOLVER PROBE
# ==============================================================================
source "$(dirname "$0")/../../core/environment.sh"
source "$TOOLKIT_CORE/logger.sh"

log_info "Kiểm tra rò rỉ DNS & Tốc độ phân giải..."
$PYTHON_CMD -c "from network.deep_interceptor import DNSInterceptEngine; leak = DNSInterceptEngine.check_dns_leak(); print(f'Trạng thái: {leak[\"leak_status\"]} | IP: {leak[\"resolved_ip\"]} | Ping: {leak[\"latency_ms\"]} ms')"
$PYTHON_CMD -c "from network.dns import DNSResolver; res = DNSResolver.test_all_dns_servers(); [print(f'-> {k:<20}: {v:.1f} ms') for k, v in res.items()]"
