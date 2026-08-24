// ==============================================================================
// Roblox Multi-Tag Controller - Native C++ Hardware Probe Engine
// High-Precision Nanosecond Hardware Introspection (Windows & Android Linux)
// ==============================================================================

#ifdef _WIN32
    #define WIN32_LEAN_AND_MEAN
    #include <windows.h>
    #include <psapi.h>
    #pragma comment(lib, "psapi.lib")
    #define EXPORT_API extern "C" __declspec(dllexport)
#else
    #include <sys/sysinfo.h>
    #include <sys/statvfs.h>
    #include <unistd.h>
    #include <fcntl.h>
    #include <stdio.h>
    #include <stdlib.h>
    #include <string.h>
    #define EXPORT_API extern "C" __attribute__((visibility("default")))
#endif

#include <stdint.h>

#ifdef _WIN32
static uint64_t filetime_to_uint64(const FILETIME& ft) {
    return ((uint64_t)ft.dwHighDateTime << 32) | (uint64_t)ft.dwLowDateTime;
}

static uint64_t g_prev_idle = 0;
static uint64_t g_prev_kernel = 0;
static uint64_t g_prev_user = 0;
#else
static uint64_t g_prev_cpu_idle = 0;
static uint64_t g_prev_cpu_total = 0;
#endif

// ------------------------------------------------------------------------------
// 1. Đo lường tỷ lệ sử dụng CPU thời gian thực với độ chính xác đến từng nano-giây
// ------------------------------------------------------------------------------
EXPORT_API double get_cpu_usage_precise() {
#ifdef _WIN32
    FILETIME idle_time, kernel_time, user_time;
    if (!GetSystemTimes(&idle_time, &kernel_time, &user_time)) {
        return 0.0;
    }

    uint64_t cur_idle = filetime_to_uint64(idle_time);
    uint64_t cur_kernel = filetime_to_uint64(kernel_time);
    uint64_t cur_user = filetime_to_uint64(user_time);

    if (g_prev_kernel == 0 && g_prev_user == 0) {
        g_prev_idle = cur_idle;
        g_prev_kernel = cur_kernel;
        g_prev_user = cur_user;
        return 15.0; // Baseline khởi động
    }

    uint64_t delta_idle = cur_idle - g_prev_idle;
    uint64_t delta_kernel = cur_kernel - g_prev_kernel;
    uint64_t delta_user = cur_user - g_prev_user;
    uint64_t total_sys = delta_kernel + delta_user;

    g_prev_idle = cur_idle;
    g_prev_kernel = cur_kernel;
    g_prev_user = cur_user;

    if (total_sys == 0) return 0.0;
    double cpu_usage = (1.0 - ((double)delta_idle / (double)total_sys)) * 100.0;
    if (cpu_usage < 0.0) cpu_usage = 0.0;
    if (cpu_usage > 100.0) cpu_usage = 100.0;
    return cpu_usage;
#else
    // Android / Linux: Đọc trực tiếp jiffies từ Linux Kernel /proc/stat
    FILE* fp = fopen("/proc/stat", "r");
    if (!fp) return 0.0;

    char line[256];
    unsigned long long user, nice, system, idle, iowait, irq, softirq, steal;
    if (!fgets(line, sizeof(line), fp)) {
        fclose(fp);
        return 0.0;
    }
    fclose(fp);

    if (sscanf(line, "cpu %llu %llu %llu %llu %llu %llu %llu %llu",
               &user, &nice, &system, &idle, &iowait, &irq, &softirq, &steal) < 4) {
        return 0.0;
    }

    unsigned long long cur_idle = idle + iowait;
    unsigned long long cur_total = user + nice + system + idle + iowait + irq + softirq + steal;

    if (g_prev_cpu_total == 0) {
        g_prev_cpu_idle = cur_idle;
        g_prev_cpu_total = cur_total;
        return 10.0;
    }

    unsigned long long delta_idle = cur_idle - g_prev_cpu_idle;
    unsigned long long delta_total = cur_total - g_prev_cpu_total;

    g_prev_cpu_idle = cur_idle;
    g_prev_cpu_total = cur_total;

    if (delta_total == 0) return 0.0;
    double cpu_usage = (1.0 - ((double)delta_idle / (double)delta_total)) * 100.0;
    if (cpu_usage < 0.0) cpu_usage = 0.0;
    if (cpu_usage > 100.0) cpu_usage = 100.0;
    return cpu_usage;
#endif
}

// ------------------------------------------------------------------------------
// 2. Đo lường RAM máy tính chính xác từng Byte (Physical Memory Introspection)
// ------------------------------------------------------------------------------
EXPORT_API int get_ram_info_precise(uint64_t* total_bytes, uint64_t* avail_bytes, uint64_t* used_bytes, double* percent) {
#ifdef _WIN32
    MEMORYSTATUSEX mem_status;
    mem_status.dwLength = sizeof(MEMORYSTATUSEX);
    if (!GlobalMemoryStatusEx(&mem_status)) {
        return -1;
    }

    if (total_bytes) *total_bytes = mem_status.ullTotalPhys;
    if (avail_bytes) *avail_bytes = mem_status.ullAvailPhys;
    if (used_bytes)  *used_bytes  = mem_status.ullTotalPhys - mem_status.ullAvailPhys;
    if (percent)     *percent     = (double)mem_status.dwMemoryLoad;
    return 0;
#else
    // Android / Linux Kernel sysinfo & /proc/meminfo
    struct sysinfo s_info;
    if (sysinfo(&s_info) == 0) {
        uint64_t total = (uint64_t)s_info.totalram * (uint64_t)s_info.mem_unit;
        uint64_t free_ram = ((uint64_t)s_info.freeram + (uint64_t)s_info.bufferram) * (uint64_t)s_info.mem_unit;
        
        // Thử đọc MemAvailable chuẩn xác nhất từ /proc/meminfo
        FILE* fp = fopen("/proc/meminfo", "r");
        if (fp) {
            char line[128];
            unsigned long long mem_avail_kb = 0;
            while (fgets(line, sizeof(line), fp)) {
                if (sscanf(line, "MemAvailable: %llu kB", &mem_avail_kb) == 1) {
                    free_ram = mem_avail_kb * 1024ULL;
                    break;
                }
            }
            fclose(fp);
        }

        uint64_t used = (total > free_ram) ? (total - free_ram) : 0;
        double pct = total > 0 ? ((double)used / (double)total) * 100.0 : 0.0;

        if (total_bytes) *total_bytes = total;
        if (avail_bytes) *avail_bytes = free_ram;
        if (used_bytes)  *used_bytes  = used;
        if (percent)     *percent     = pct;
        return 0;
    }
    return -1;
#endif
}

// ------------------------------------------------------------------------------
// 3. Đo lường dung lượng Ổ cứng (Disk Storage Space) chuẩn xác đến từng Sector
// ------------------------------------------------------------------------------
EXPORT_API int get_disk_info_precise(const char* mount_path, uint64_t* total_bytes, uint64_t* free_bytes, uint64_t* used_bytes, double* percent) {
#ifdef _WIN32
    ULARGE_INTEGER free_bytes_avail, total_num_bytes, total_free_bytes;
    const char* path_to_check = (mount_path && strlen(mount_path) > 0) ? mount_path : "C:\\";
    
    WCHAR w_path[MAX_PATH];
    MultiByteToWideChar(CP_UTF8, 0, path_to_check, -1, w_path, MAX_PATH);

    if (!GetDiskFreeSpaceExW(w_path, &free_bytes_avail, &total_num_bytes, &total_free_bytes)) {
        return -1;
    }

    uint64_t total = total_num_bytes.QuadPart;
    uint64_t free_b = free_bytes_avail.QuadPart;
    uint64_t used = (total > free_b) ? (total - free_b) : 0;
    double pct = total > 0 ? ((double)used / (double)total) * 100.0 : 0.0;

    if (total_bytes) *total_bytes = total;
    if (free_bytes)  *free_bytes  = free_b;
    if (used_bytes)  *used_bytes  = used;
    if (percent)     *percent     = pct;
    return 0;
#else
    struct statvfs s_vfs;
    const char* path_to_check = (mount_path && strlen(mount_path) > 0) ? mount_path : "/";
    if (statvfs(path_to_check, &s_vfs) == 0) {
        uint64_t total = (uint64_t)s_vfs.f_blocks * (uint64_t)s_vfs.f_frsize;
        uint64_t free_b = (uint64_t)s_vfs.f_bavail * (uint64_t)s_vfs.f_frsize;
        uint64_t used = (total > free_b) ? (total - free_b) : 0;
        double pct = total > 0 ? ((double)used / (double)total) * 100.0 : 0.0;

        if (total_bytes) *total_bytes = total;
        if (free_bytes)  *free_bytes  = free_b;
        if (used_bytes)  *used_bytes  = used;
        if (percent)     *percent     = pct;
        return 0;
    }
    return -1;
#endif
}

// ------------------------------------------------------------------------------
// 4. Đo lường RAM của tiến trình Roblox Client thực tế (Working Set & Private Memory)
// ------------------------------------------------------------------------------
EXPORT_API int get_roblox_process_memory(int pid, uint64_t* working_set_bytes, uint64_t* private_bytes) {
#ifdef _WIN32
    HANDLE h_proc = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, (DWORD)pid);
    if (!h_proc) {
        return -1;
    }

    PROCESS_MEMORY_COUNTERS_EX pmc;
    if (GetProcessMemoryInfo(h_proc, (PROCESS_MEMORY_COUNTERS*)&pmc, sizeof(pmc))) {
        if (working_set_bytes) *working_set_bytes = pmc.WorkingSetSize;
        if (private_bytes)     *private_bytes     = pmc.PrivateUsage;
        CloseHandle(h_proc);
        return 0;
    }
    CloseHandle(h_proc);
    return -1;
#else
    // Android / Linux: Đọc từ /proc/[pid]/statm
    char statm_path[64];
    snprintf(statm_path, sizeof(statm_path), "/proc/%d/statm", pid);
    FILE* fp = fopen(statm_path, "r");
    if (!fp) return -1;

    unsigned long size, resident, share, text, lib, data, dt;
    if (fscanf(fp, "%lu %lu %lu %lu %lu %lu %lu", &size, &resident, &share, &text, &lib, &data, &dt) >= 2) {
        long page_size = sysconf(_SC_PAGESIZE);
        if (working_set_bytes) *working_set_bytes = (uint64_t)resident * (uint64_t)page_size;
        if (private_bytes)     *private_bytes     = ((uint64_t)resident - (uint64_t)share) * (uint64_t)page_size;
        fclose(fp);
        return 0;
    }
    fclose(fp);
    return -1;
#endif
}
