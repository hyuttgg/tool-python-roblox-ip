#!/usr/bin/env bash
# ==============================================================================
# DEPENDENCY MANAGER
# ==============================================================================

check_command() {
    command -v "$1" >/dev/null 2>&1
}

install_termux_package() {
    local pkg="$1"
    if check_command "$pkg"; then
        log_success "Package '$pkg' đã được cài đặt."
        return 0
    fi
    log_info "Đang cài đặt '$pkg' qua pkg..."
    pkg install -y "$pkg" >/dev/null 2>&1 || apt-get install -y "$pkg" >/dev/null 2>&1
}

install_all_dependencies() {
    log_info "Cập nhật kho gói Termux..."
    pkg update -y >/dev/null 2>&1 || true

    local pkgs=(
        git
        curl
        wget
        python
        tsu
        root-repo
        tar
        unzip
        openjdk-17
        clang
        jq
        iptables
    )

    for p in "${pkgs[@]}"; do
        install_termux_package "$p"
    done

    # Cài đặt python dependencies
    if [ -f "$TOOLKIT_ROOT/requirements.txt" ]; then
        log_info "Cài đặt Python requirements..."
        pip install --upgrade pip >/dev/null 2>&1 || true
        pip install -r "$TOOLKIT_ROOT/requirements.txt" >/dev/null 2>&1 || true
    fi
}
