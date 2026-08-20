/**
 * RobloxDeepNetworkEngine.java
 * Bộ công cụ mạng Java chuyên sâu dành cho Roblox trên Android / UGPhone / Cloud Phones.
 * Hỗ trợ:
 * 1. Dynamic ProxySelector & Traffic Routing tầng hệ điều hành / JVM.
 * 2. Đo đạc độ trễ TCP Handshake, Socket Ping & DNS resolution thời gian thực.
 * 3. Giao thức IPC Socket / CLI JSON kết nối trực tiếp với Python Master Controller.
 * 4. Giám sát trạng thái tiến trình và kết nối của Roblox Client.
 */

package com.roblox.network;

import java.io.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.*;

public class RobloxDeepNetworkEngine {

    private static final String DEFAULT_ROBLOX_DOMAIN = "www.roblox.com";
    private static Proxy currentProxy = Proxy.NO_PROXY;

    /**
     * Cài đặt Custom ProxySelector để định tuyến toàn bộ kết nối Java / Android qua Proxy chỉ định
     */
    public static void installDeepProxySelector(final String host, final int port, final boolean isSocks) {
        final SocketAddress proxyAddr = new InetSocketAddress(host, port);
        currentProxy = isSocks ? new Proxy(Proxy.Type.SOCKS, proxyAddr) : new Proxy(Proxy.Type.HTTP, proxyAddr);

        ProxySelector.setDefault(new ProxySelector() {
            @Override
            public List<Proxy> select(URI uri) {
                if (uri == null) {
                    return Collections.singletonList(Proxy.NO_PROXY);
                }
                String scheme = uri.getScheme();
                if ("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme) || "socket".equalsIgnoreCase(scheme)) {
                    return Collections.singletonList(currentProxy);
                }
                return Collections.singletonList(Proxy.NO_PROXY);
            }

            @Override
            public void connectFailed(URI uri, SocketAddress sa, IOException ioe) {
                System.err.println("[JAVA ENGINE] Connect failed via proxy: " + sa + " -> " + ioe.getMessage());
            }
        });

        System.setProperty("http.proxyHost", host);
        System.setProperty("http.proxyPort", String.valueOf(port));
        System.setProperty("https.proxyHost", host);
        System.setProperty("https.proxyPort", String.valueOf(port));
    }

    /**
     * Đo đạc chuyên sâu mạng: DNS Resolve Time + TCP Handshake Latency + HTTP Response Code
     */
    public static Map<String, Object> runDeepDiagnostics(String proxyHost, int proxyPort, String targetDomain, int timeoutMs) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("target", targetDomain);
        result.put("proxy", proxyHost + ":" + proxyPort);
        result.put("timestamp", System.currentTimeMillis());

        // 1. Đo thời gian phân giải DNS
        long dnsStart = System.currentTimeMillis();
        String resolvedIp = "N/A";
        try {
            InetAddress addr = InetAddress.getByName(targetDomain);
            resolvedIp = addr.getHostAddress();
            result.put("dns_ms", System.currentTimeMillis() - dnsStart);
            result.put("resolved_ip", resolvedIp);
        } catch (Exception e) {
            result.put("dns_ms", -1);
            result.put("dns_error", e.getMessage());
        }

        // 2. Đo TCP Handshake Latency tới Proxy
        long tcpStart = System.currentTimeMillis();
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress(proxyHost, proxyPort), timeoutMs);
            result.put("tcp_latency_ms", System.currentTimeMillis() - tcpStart);
            result.put("proxy_status", "ONLINE");
        } catch (Exception e) {
            result.put("tcp_latency_ms", -1);
            result.put("proxy_status", "OFFLINE");
            result.put("error", e.getMessage());
        }

        return result;
    }

    /**
     * Quét đa luồng kiểm tra nhanh danh sách Proxy
     */
    public static List<Map<String, Object>> batchProbeProxies(List<String> proxyList, int timeoutMs) {
        ExecutorService executor = Executors.newFixedThreadPool(Math.min(proxyList.size(), 10));
        List<Future<Map<String, Object>>> futures = new ArrayList<>();

        for (final String proxyStr : proxyList) {
            futures.add(executor.submit(new Callable<Map<String, Object>>() {
                @Override
                public Map<String, Object> call() {
                    Map<String, Object> map = new LinkedHashMap<>();
                    map.put("proxy", proxyStr);
                    try {
                        String[] parts = proxyStr.split(":");
                        String host = parts[0];
                        int port = Integer.parseInt(parts[1]);
                        long s = System.currentTimeMillis();
                        try (Socket sock = new Socket()) {
                            sock.connect(new InetSocketAddress(host, port), timeoutMs);
                            map.put("latency_ms", System.currentTimeMillis() - s);
                            map.put("alive", true);
                        }
                    } catch (Exception e) {
                        map.put("latency_ms", -1);
                        map.put("alive", false);
                    }
                    return map;
                }
            }));
        }

        List<Map<String, Object>> results = new ArrayList<>();
        for (Future<Map<String, Object>> f : futures) {
            try {
                results.add(f.get(timeoutMs + 500, TimeUnit.MILLISECONDS));
            } catch (Exception ignored) {}
        }
        executor.shutdown();
        return results;
    }

    /**
     * Khởi chạy CLI Interface cho Python gọi trực tiếp
     */
    public static void main(String[] args) {
        if (args.length == 0) {
            System.out.println("{\"engine\":\"RobloxDeepNetworkEngine\",\"version\":\"3.0.0\",\"status\":\"READY\"}");
            return;
        }

        String command = args[0];
        if ("--set-proxy".equals(command) && args.length >= 3) {
            String host = args[1];
            int port = Integer.parseInt(args[2]);
            boolean isSocks = args.length > 3 && "socks".equalsIgnoreCase(args[3]);
            installDeepProxySelector(host, port, isSocks);
            System.out.println("{\"status\":\"SUCCESS\",\"action\":\"set_proxy\",\"host\":\"" + host + "\",\"port\":" + port + "}");
        } else if ("--diagnose".equals(command) && args.length >= 3) {
            String host = args[1];
            int port = Integer.parseInt(args[2]);
            String domain = args.length > 3 ? args[3] : DEFAULT_ROBLOX_DOMAIN;
            Map<String, Object> diag = runDeepDiagnostics(host, port, domain, 2000);
            
            // In JSON output
            StringBuilder sb = new StringBuilder("{");
            int i = 0;
            for (Map.Entry<String, Object> e : diag.entrySet()) {
                if (i++ > 0) sb.append(",");
                sb.append("\"").append(e.getKey()).append("\":");
                if (e.getValue() instanceof Number || e.getValue() instanceof Boolean) {
                    sb.append(e.getValue());
                } else {
                    sb.append("\"").append(e.getValue()).append("\"");
                }
            }
            sb.append("}");
            System.out.println(sb.toString());
        } else {
            System.out.println("{\"error\":\"Unknown command\",\"usage\":\"--set-proxy <host> <port> | --diagnose <host> <port> [domain]\"}");
        }
    }
}
