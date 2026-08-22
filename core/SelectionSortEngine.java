// -*- coding: utf-8 -*-
/*
 * ========================================================================================
 *      ROBLOX SELECTION SORT ENGINE (JAVA HIGH-PERFORMANCE ALGORITHM CORE)
 * ========================================================================================
 * Thuật toán Sắp xếp Chọn (Selection Sort) chuyên dụng cho việc tối ưu hóa gán IP & Proxy:
 *  1. Chia danh sách Proxy thành 2 phân vùng: [Đã sắp xếp] và [Chưa sắp xếp].
 *  2. Liên tục tìm Proxy có độ trễ (Latency/Ping ms) nhỏ nhất trong vùng chưa sắp xếp.
 *  3. Hoán đổi (Swap) phần tử nhỏ nhất về vị trí đầu tiên của vùng chưa sắp xếp.
 *  4. Lặp lại cho đến khi toàn bộ dải IP được sắp xếp theo thứ tự Ping từ thấp nhất -> cao nhất.
 * ========================================================================================
 */

package com.roblox.algorithm;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

public class SelectionSortEngine {

    public static class ProxyItem {
        public String ip;
        public int latencyMs;
        public String region;
        public String country;
        public String tagId;

        public ProxyItem(String ip, int latencyMs, String region, String country, String tagId) {
            this.ip = ip;
            this.latencyMs = latencyMs;
            this.region = region != null ? region : "[JP] Japan Dedicated";
            this.country = country != null ? country : "JP";
            this.tagId = tagId != null ? tagId : "ROBLOX-TAG";
        }
    }

    public static class SortStepLog {
        public int pass;
        public int minIdx;
        public int swappedWithIdx;
        public String minIp;
        public int minLatency;

        public SortStepLog(int pass, int minIdx, int swappedWithIdx, String minIp, int minLatency) {
            this.pass = pass;
            this.minIdx = minIdx;
            this.swappedWithIdx = swappedWithIdx;
            this.minIp = minIp;
            this.minLatency = minLatency;
        }
    }

    /**
     * Thuật toán Selection Sort kinh điển
     */
    public static List<ProxyItem> sortProxiesByLatency(List<ProxyItem> list, List<SortStepLog> stepLogs) {
        int n = list.size();
        for (int i = 0; i < n - 1; i++) {
            int minIndex = i;
            for (int j = i + 1; j < n; j++) {
                if (list.get(j).latencyMs < list.get(minIndex).latencyMs) {
                    minIndex = j;
                }
            }

            // Ghi nhận bước hoán đổi (Step Trace)
            if (stepLogs != null) {
                stepLogs.add(new SortStepLog(i + 1, minIndex, i, list.get(minIndex).ip, list.get(minIndex).latencyMs));
            }

            // Thực hiện hoán đổi vị trí (Swap)
            if (minIndex != i) {
                ProxyItem temp = list.get(i);
                list.set(i, list.get(minIndex));
                list.set(minIndex, temp);
            }
        }
        return list;
    }

    public static void main(String[] args) {
        try {
            BufferedReader reader = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }

            String inputJson = sb.toString().trim();
            if (inputJson.isEmpty() && args.length > 0) {
                inputJson = args[0];
            }

            // Parse Simple JSON Array of objects
            List<ProxyItem> items = parseSimpleJson(inputJson);
            List<SortStepLog> logs = new ArrayList<>();
            List<ProxyItem> sorted = sortProxiesByLatency(items, logs);

            // Output JSON string
            System.out.println(buildOutputJson(sorted, logs));

        } catch (Exception e) {
            System.err.println("{\"error\": \"" + e.getMessage() + "\"}");
            System.exit(1);
        }
    }

    private static List<ProxyItem> parseSimpleJson(String json) {
        List<ProxyItem> list = new ArrayList<>();
        if (json == null || json.length() < 3) return list;

        // Tách các object trong mảng
        String trimmed = json.trim();
        if (trimmed.startsWith("[")) trimmed = trimmed.substring(1);
        if (trimmed.endsWith("]")) trimmed = trimmed.substring(0, trimmed.length() - 1);

        String[] objTokens = trimmed.split("\\},\\s*\\{");
        for (String tok : objTokens) {
            tok = tok.replace("{", "").replace("}", "").trim();
            String ip = extractField(tok, "ip", "127.0.0.1:80");
            int lat = extractIntField(tok, "latency_ms", 999);
            String reg = extractField(tok, "region", "[JP] Japan Dedicated");
            String country = extractField(tok, "country", "JP");
            String tagId = extractField(tok, "tag_id", "ROBLOX-TAG");
            list.add(new ProxyItem(ip, lat, reg, country, tagId));
        }
        return list;
    }

    private static String extractField(String text, String key, String defaultVal) {
        String target = "\"" + key + "\":";
        int idx = text.indexOf(target);
        if (idx == -1) return defaultVal;
        int start = idx + target.length();
        String sub = text.substring(start).trim();
        if (sub.startsWith("\"")) {
            int endQuote = sub.indexOf("\"", 1);
            if (endQuote != -1) {
                return sub.substring(1, endQuote);
            }
        }
        int comma = sub.indexOf(",");
        if (comma != -1) return sub.substring(0, comma).trim().replace("\"", "");
        return sub.replace("\"", "").trim();
    }

    private static int extractIntField(String text, String key, int defaultVal) {
        try {
            String val = extractField(text, key, String.valueOf(defaultVal));
            return Integer.parseInt(val.replaceAll("[^0-9]", ""));
        } catch (Exception e) {
            return defaultVal;
        }
    }

    private static String buildOutputJson(List<ProxyItem> sorted, List<SortStepLog> logs) {
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"status\": \"success\",\n");
        sb.append("  \"algorithm\": \"Selection Sort (Java 8 Core Engine)\",\n");
        sb.append("  \"total_items\": ").append(sorted.size()).append(",\n");
        
        sb.append("  \"steps_count\": ").append(logs.size()).append(",\n");
        sb.append("  \"sorted_proxies\": [\n");
        for (int i = 0; i < sorted.size(); i++) {
            ProxyItem item = sorted.get(i);
            sb.append("    {");
            sb.append("\"rank\": ").append(i + 1).append(", ");
            sb.append("\"ip\": \"").append(item.ip).append("\", ");
            sb.append("\"latency_ms\": ").append(item.latencyMs).append(", ");
            sb.append("\"region\": \"").append(item.region).append("\", ");
            sb.append("\"country\": \"").append(item.country).append("\", ");
            sb.append("\"tag_id\": \"").append(item.tagId).append("\"");
            sb.append("}");
            if (i < sorted.size() - 1) sb.append(",");
            sb.append("\n");
        }
        sb.append("  ]\n");
        sb.append("}");
        return sb.toString();
    }
}
