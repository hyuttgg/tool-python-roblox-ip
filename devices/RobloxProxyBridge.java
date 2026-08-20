/**
 * RobloxProxyBridge.java
 * Helper class Java tương thích Android / UGPhone / Cloud Phones
 * Hỗ trợ cấu hình Network Proxy, kiểm tra Socket Ping và phát hiện Roblox Client trên Android.
 */

package com.roblox.network;

import java.io.*;
import java.net.*;

public class RobloxProxyBridge {

    /**
     * Kiểm tra kết nối và độ trễ Ping tới Proxy
     */
    public static int pingProxy(String host, int port, int timeoutMs) {
        long start = System.currentTimeMillis();
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress(host, port), timeoutMs);
            return (int) (System.currentTimeMillis() - start);
        } catch (Exception e) {
            return -1;
        }
    }

    /**
     * Tạo thiết lập HTTP Proxy cho JVM / Android Environment
     */
    public static void setSystemProxy(String host, int port) {
        System.setProperty("http.proxyHost", host);
        System.setProperty("http.proxyPort", String.valueOf(port));
        System.setProperty("https.proxyHost", host);
        System.setProperty("https.proxyPort", String.valueOf(port));
    }

    /**
     * Xóa thiết lập Proxy
     */
    public static void clearSystemProxy() {
        System.clearProperty("http.proxyHost");
        System.clearProperty("http.proxyPort");
        System.clearProperty("https.proxyHost");
        System.clearProperty("https.proxyPort");
    }

    public static void main(String[] args) {
        if (args.length >= 2) {
            String host = args[0];
            int port = Integer.parseInt(args[1]);
            int latency = pingProxy(host, port, 1500);
            System.out.println("{\"proxy\":\"" + host + ":" + port + "\",\"latency_ms\":" + latency + "}");
        } else {
            System.out.println("Usage: java RobloxProxyBridge <host> <port>");
        }
    }
}
