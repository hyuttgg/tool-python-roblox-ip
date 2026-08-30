package com.roblox.network;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.ReentrantReadWriteLock;

/**
 * RobloxLeastConnectionsBalancer.java
 * Thuật toán Cân bằng tải Kết nối ít nhất (Least Connections Load Balancer) cho Roblox Multi-Accounts / Clones.
 * Tương thích: JVM / Android UGPhone / Cloud Phones & CLI Bridge.
 */
public class RobloxLeastConnectionsBalancer {

    /**
     * Đại diện cho một Proxy Node trong hệ thống
     */
    public static class ProxyNode {
        private final String proxyId;
        private final String host;
        private final int port;
        private final String protocol;
        private final String username;
        private final String password;
        private final int maxConnections;
        private final int weight;
        private final String country;

        private volatile int latencyMs;
        private volatile boolean isHealthy;
        private volatile long lastAssignedTime;

        private final AtomicInteger activeConnections = new AtomicInteger(0);
        private final AtomicInteger totalServed = new AtomicInteger(0);

        public ProxyNode(
                String proxyId,
                String host,
                int port,
                String protocol,
                String username,
                String password,
                int maxConnections,
                int weight,
                int latencyMs,
                String country) {
            this.proxyId = proxyId;
            this.host = host;
            this.port = port;
            this.protocol = protocol != null ? protocol.toLowerCase() : "socks5";
            this.username = username;
            this.password = password;
            this.maxConnections = Math.max(1, maxConnections);
            this.weight = Math.max(1, weight);
            this.latencyMs = latencyMs;
            this.country = country != null ? country.toUpperCase() : "MULTI";
            this.isHealthy = true;
            this.lastAssignedTime = 0L;
        }

        public String getEndpoint() {
            if (username != null && !username.isEmpty() && password != null && !password.isEmpty()) {
                return protocol + "://" + username + ":" + password + "@" + host + ":" + port;
            }
            return protocol + "://" + host + ":" + port;
        }

        public boolean isAvailable() {
            return isHealthy && (activeConnections.get() < maxConnections);
        }

        public double getLoadRatio() {
            return (double) activeConnections.get() / weight;
        }

        // Getters & Setters
        public String getProxyId() { return proxyId; }
        public String getHost() { return host; }
        public int getPort() { return port; }
        public String getProtocol() { return protocol; }
        public int getMaxConnections() { return maxConnections; }
        public int getWeight() { return weight; }
        public String getCountry() { return country; }
        public int getLatencyMs() { return latencyMs; }
        public void setLatencyMs(int latencyMs) { this.latencyMs = latencyMs; }
        public boolean isHealthy() { return isHealthy; }
        public void setHealthy(boolean healthy) { this.isHealthy = healthy; }
        public int getActiveConnections() { return activeConnections.get(); }
        public int getTotalServed() { return totalServed.get(); }
        public long getLastAssignedTime() { return lastAssignedTime; }
        public void setLastAssignedTime(long time) { this.lastAssignedTime = time; }

        public void incrementConnection() {
            activeConnections.incrementAndGet();
            totalServed.incrementAndGet();
            lastAssignedTime = System.currentTimeMillis();
        }

        public void decrementConnection() {
            activeConnections.updateAndGet(val -> Math.max(0, val - 1));
        }

        public String toJson() {
            return String.format(
                "{\"proxy_id\":\"%s\",\"host\":\"%s\",\"port\":%d,\"protocol\":\"%s\",\"endpoint\":\"%s\"," +
                "\"max_connections\":%d,\"active_connections\":%d,\"load_ratio\":%.2f,\"weight\":%d," +
                "\"latency_ms\":%d,\"country\":\"%s\",\"is_healthy\":%b,\"total_served\":%d}",
                proxyId, host, port, protocol, getEndpoint(),
                maxConnections, activeConnections.get(), getLoadRatio(), weight,
                latencyMs, country, isHealthy, totalServed.get()
            );
        }
    }

    private final Map<String, ProxyNode> proxies = new ConcurrentHashMap<>();
    private final Map<String, String> accountMap = new ConcurrentHashMap<>(); // accountId -> proxyId
    private final ReentrantReadWriteLock rwLock = new ReentrantReadWriteLock();
    private final int defaultMaxPerProxy;

    public RobloxLeastConnectionsBalancer(int defaultMaxPerProxy) {
        this.defaultMaxPerProxy = defaultMaxPerProxy > 0 ? defaultMaxPerProxy : 5;
    }

    public void addProxy(
            String proxyId,
            String host,
            int port,
            String protocol,
            String username,
            String password,
            int maxConnections,
            int weight,
            int latencyMs,
            String country) {
        rwLock.writeLock().lock();
        try {
            int limit = maxConnections > 0 ? maxConnections : defaultMaxPerProxy;
            ProxyNode node = new ProxyNode(proxyId, host, port, protocol, username, password, limit, weight, latencyMs, country);
            proxies.put(proxyId, node);
        } finally {
            rwLock.writeLock().unlock();
        }
    }

    public void setHealthStatus(String proxyId, boolean isHealthy, int latencyMs) {
        rwLock.writeLock().lock();
        try {
            ProxyNode node = proxies.get(proxyId);
            if (node != null) {
                node.setHealthy(isHealthy);
                if (latencyMs >= 0) {
                    node.setLatencyMs(latencyMs);
                }
            }
        } finally {
            rwLock.writeLock().unlock();
        }
    }

    /**
     * Cấp phát Proxy theo thuật toán Kết nối ít nhất (Least Connections)
     */
    public ProxyNode allocateProxy(String accountId, String preferredCountry) {
        rwLock.writeLock().lock();
        try {
            // 1. Kiểm tra session hiện có
            if (accountMap.containsKey(accountId)) {
                String existingId = accountMap.get(accountId);
                ProxyNode existingNode = proxies.get(existingId);
                if (existingNode != null && existingNode.isHealthy()) {
                    return existingNode;
                } else {
                    accountMap.remove(accountId);
                }
            }

            // 2. Tìm danh sách ứng viên
            List<ProxyNode> candidates = new ArrayList<>();
            for (ProxyNode node : proxies.values()) {
                if (node.isAvailable()) {
                    if (preferredCountry == null || "MULTI".equalsIgnoreCase(preferredCountry)
                            || node.getCountry().equalsIgnoreCase(preferredCountry)) {
                        candidates.add(node);
                    }
                }
            }

            // Fallback nếu không có proxy đúng quốc gia yêu cầu
            if (candidates.isEmpty() && preferredCountry != null && !"MULTI".equalsIgnoreCase(preferredCountry)) {
                for (ProxyNode node : proxies.values()) {
                    if (node.isAvailable()) {
                        candidates.add(node);
                    }
                }
            }

            if (candidates.isEmpty()) {
                return null;
            }

            // 3. Chọn Proxy có:
            //    - Tải ít nhất (activeConnections / weight)
            //    - Nếu bằng nhau: Ping thấp nhất (latencyMs)
            //    - Nếu bằng nhau: Ít lượt phục vụ nhất (totalServed)
            ProxyNode best = candidates.get(0);
            for (int i = 1; i < candidates.size(); i++) {
                ProxyNode cur = candidates.get(i);
                if (cur.getLoadRatio() < best.getLoadRatio()) {
                    best = cur;
                } else if (Double.compare(cur.getLoadRatio(), best.getLoadRatio()) == 0) {
                    if (cur.getLatencyMs() < best.getLatencyMs()) {
                        best = cur;
                    } else if (cur.getLatencyMs() == best.getLatencyMs()) {
                        if (cur.getTotalServed() < best.getTotalServed()) {
                            best = cur;
                        }
                    }
                }
            }

            // 4. Đăng ký session
            best.incrementConnection();
            accountMap.put(accountId, best.getProxyId());
            return best;
        } finally {
            rwLock.writeLock().unlock();
        }
    }

    /**
     * Giải phóng kết nối khi tài khoản đăng xuất hoặc crash
     */
    public boolean releaseProxy(String accountId) {
        rwLock.writeLock().lock();
        try {
            String proxyId = accountMap.remove(accountId);
            if (proxyId == null) return false;

            ProxyNode node = proxies.get(proxyId);
            if (node != null) {
                node.decrementConnection();
                return true;
            }
            return false;
        } finally {
            rwLock.writeLock().unlock();
        }
    }

    public String getPoolStatusJson() {
        rwLock.readLock().lock();
        try {
            StringBuilder sb = new StringBuilder();
            sb.append("[");
            boolean first = true;
            for (ProxyNode node : proxies.values()) {
                if (!first) sb.append(",");
                sb.append(node.toJson());
                first = false;
            }
            sb.append("]");
            return sb.toString();
        } finally {
            rwLock.readLock().unlock();
        }
    }

    // =========================================================================
    // MAIN DEMO & CLI EXECUTION
    // =========================================================================
    public static void main(String[] args) {
        System.out.println("===============================================================");
        System.out.println(" ROBLOX LEAST CONNECTIONS LOAD BALANCER ENGINE (JAVA / ANDROID)");
        System.out.println("===============================================================");

        RobloxLeastConnectionsBalancer balancer = new RobloxLeastConnectionsBalancer(3);

        // Nạp các proxy mẫu
        balancer.addProxy("Proxy_US_East", "104.28.1.1", 1080, "socks5", "", "", 3, 1, 40, "US");
        balancer.addProxy("Proxy_US_West", "104.28.1.2", 1080, "socks5", "", "", 3, 1, 20, "US");
        balancer.addProxy("Proxy_SG_Fast", "103.15.2.1", 1080, "socks5", "", "", 3, 1, 15, "SG");
        balancer.addProxy("Proxy_JP_Node", "133.242.1.1", 1080, "socks5", "", "", 3, 1, 55, "JP");

        System.out.println("\n[1] Đang gán 8 Clone Roblox tuần tự vào Pool:");
        for (int i = 1; i <= 8; i++) {
            String acc = "Clone_Acc_" + i;
            ProxyNode assigned = balancer.allocateProxy(acc, "MULTI");
            if (assigned != null) {
                System.out.printf(" -> %-12s => Gán vào: %-15s (Tải hiện tại: %d/%d, Ping: %dms)%n",
                        acc, assigned.getProxyId(), assigned.getActiveConnections(), assigned.getMaxConnections(), assigned.getLatencyMs());
            } else {
                System.out.printf(" -> %-12s => THẤT BẠI: Hết Proxy khả dụng!%n", acc);
            }
        }

        System.out.println("\n[2] Giả lập: Clone_Acc_1 và Clone_Acc_2 ngắt kết nối (Release):");
        balancer.releaseProxy("Clone_Acc_1");
        balancer.releaseProxy("Clone_Acc_2");
        System.out.println(" -> Đã giải phóng Clone_Acc_1 & Clone_Acc_2.");

        System.out.println("\n[3] Đẩy tài khoản mới Clone_Acc_9 vào hệ thống:");
        ProxyNode next = balancer.allocateProxy("Clone_Acc_9", "MULTI");
        if (next != null) {
            System.out.printf(" -> Clone_Acc_9 tự động chọn IP có kết nối ít nhất: %s (Đang có %d kết nối)%n",
                    next.getProxyId(), next.getActiveConnections());
        }

        System.out.println("\n[4] Dữ liệu JSON Pool Status:");
        System.out.println(balancer.getPoolStatusJson());
    }
}
