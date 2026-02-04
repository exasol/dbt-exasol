#!/bin/bash
# SSH Tunnel Management for Docker Remote Access

set -euo pipefail

PIDFILE="${TUNNEL_PIDFILE:-/tmp/docker-ssh-tunnel.pid}"
CONTROL_PATH="/tmp/docker-ssh-control-%r@%h:%p"

# Parse SSH host from DOCKER_HOST
parse_ssh_host() {
    if [[ "${DOCKER_HOST:-}" == ssh://* ]]; then
        echo "${DOCKER_HOST#ssh://}"
    else
        return 1
    fi
}

# Parse port from DBT_DSN (format: host/options:port)
parse_dbt_port() {
    if [[ "${DBT_DSN:-}" =~ :([0-9]+)$ ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        echo "8563"  # Default Exasol port
    fi
}

# Check if tunnel is running
is_running() {
    if [[ -f "$PIDFILE" ]]; then
        local pid
        pid=$(cat "$PIDFILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        else
            rm -f "$PIDFILE"
        fi
    fi
    return 1
}

# Start SSH tunnel
start_tunnel() {
    local ssh_host
    if ! ssh_host=$(parse_ssh_host); then
        echo "Error: DOCKER_HOST is not configured for SSH" >&2
        echo "Set DOCKER_HOST=ssh://user@host in .env file" >&2
        return 1
    fi

    if is_running; then
        echo "SSH tunnel is already running (PID $(cat "$PIDFILE"))"
        return 0
    fi

    local forward_port
    forward_port=$(parse_dbt_port)

    echo "Starting SSH tunnel to $ssh_host..."
    echo "Forwarding localhost:${forward_port} -> ${ssh_host}:${forward_port}"

    # Start SSH master connection in background with port forwarding
    # -M: Master mode (control socket)
    # -N: No remote command
    # -f: Background after authentication
    # -L: Local port forwarding (localhost:port -> remote:port)
    # -o ControlMaster=auto: Reuse connections
    # -o ControlPersist=yes: Keep alive
    # -o ServerAliveInterval=60: Keepalive every 60s
    # -o ServerAliveCountMax=3: Max 3 failed keepalives
    ssh -M -N -f \
        -L "${forward_port}:localhost:${forward_port}" \
        -o ControlMaster=auto \
        -o ControlPath="$CONTROL_PATH" \
        -o ControlPersist=yes \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        "$ssh_host"

    # Wait and find SSH process PID
    sleep 1
    local pid
    if pid=$(pgrep -f "ssh.*$ssh_host" | head -n1); then
        echo "$pid" > "$PIDFILE"
        echo "SSH tunnel started successfully (PID $pid)"
        echo "Docker can now connect via: $DOCKER_HOST"
        echo "Port forwarding: localhost:${forward_port} -> ${ssh_host}:${forward_port}"
        return 0
    else
        echo "Warning: SSH tunnel may have started but PID not found" >&2
        return 1
    fi
}

# Stop SSH tunnel
stop_tunnel() {
    if ! is_running; then
        echo "SSH tunnel is not running"
        return 0
    fi

    local pid
    pid=$(cat "$PIDFILE")
    echo "Stopping SSH tunnel (PID $pid)..."

    # Try graceful shutdown first
    if kill "$pid" 2>/dev/null; then
        # Wait up to 5 seconds for process to exit
        for i in {1..50}; do
            if ! kill -0 "$pid" 2>/dev/null; then
                break
            fi
            sleep 0.1
        done

        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            echo "Process did not exit gracefully, forcing..."
            kill -9 "$pid" 2>/dev/null || true
        fi
    fi

    rm -f "$PIDFILE"
    echo "SSH tunnel stopped successfully"
    return 0
}

# Show tunnel status
status_tunnel() {
    local ssh_host
    ssh_host=$(parse_ssh_host 2>/dev/null || echo "")
    
    local forward_port
    forward_port=$(parse_dbt_port)

    if is_running; then
        local pid
        pid=$(cat "$PIDFILE")
        echo "SSH tunnel is RUNNING (PID $pid)"
        echo "Docker host: ${DOCKER_HOST:-not set}"
        echo "SSH target: $ssh_host"
        echo "Port forwarding: localhost:${forward_port} -> ${ssh_host}:${forward_port}"
    else
        echo "SSH tunnel is NOT RUNNING"
        if [[ -n "$ssh_host" ]]; then
            echo "Configured for: $ssh_host"
        else
            echo "DOCKER_HOST is not configured for SSH"
        fi
    fi
    return 0
}

# Restart tunnel
restart_tunnel() {
    echo "Restarting SSH tunnel..."
    stop_tunnel
    sleep 1
    start_tunnel
}

# Main command handler
case "${1:-}" in
    start)
        start_tunnel
        ;;
    stop)
        stop_tunnel
        ;;
    status)
        status_tunnel
        ;;
    restart)
        restart_tunnel
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}" >&2
        exit 1
        ;;
esac
