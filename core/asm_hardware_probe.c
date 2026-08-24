// ==============================================================================
// Roblox Multi-Tag Controller - Low-Level Pure C & Inline Assembly Engine
// Supports: x86/x64 Inline ASM (RDTSC, CPUID) & ARM64 Inline ASM (CNTVCT_EL0)
// ==============================================================================

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#ifdef _WIN32
    #define WIN32_LEAN_AND_MEAN
    #include <windows.h>
    #include <intrin.h>
    #define C_EXPORT __declspec(dllexport)
#else
    #include <sys/time.h>
    #include <unistd.h>
    #define C_EXPORT __attribute__((visibility("default")))
#endif

// ------------------------------------------------------------------------------
// 1. HỢP NGỮ (ASSEMBLY): Đọc trực tiếp Time Stamp Counter thanh ghi phần cứng
// ------------------------------------------------------------------------------
C_EXPORT uint64_t asm_read_cpu_tsc(void) {
#if defined(_MSC_VER) || defined(__INTEL_COMPILER)
    #if defined(_M_X64) || defined(_M_IX86)
        return __rdtsc();
    #elif defined(_M_ARM64)
        return _ReadStatusReg(ARM64_CNTVCT);
    #else
        LARGE_INTEGER qpc;
        QueryPerformanceCounter(&qpc);
        return (uint64_t)qpc.QuadPart;
    #endif
#elif defined(__GNUC__) || defined(__clang__)
    #if defined(__x86_64__) || defined(__i386__)
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return ((uint64_t)hi << 32) | lo;
    #elif defined(__aarch64__)
        uint64_t val;
        __asm__ __volatile__ ("mrs %0, cntvct_el0" : "=r"(val));
        return val;
    #else
        struct timeval tv;
        gettimeofday(&tv, NULL);
        return (uint64_t)tv.tv_sec * 1000000000ULL + (uint64_t)tv.tv_usec * 1000ULL;
    #endif
#else
    return 0;
#endif
}

// ------------------------------------------------------------------------------
// 2. HỢP NGỮ (ASSEMBLY): Đọc CPU Brand String trực tiếp từ thanh ghi CPUID
// ------------------------------------------------------------------------------
C_EXPORT void asm_get_cpu_brand(char* out_brand, int max_len) {
    if (!out_brand || max_len < 16) return;
    memset(out_brand, 0, max_len);

#if (defined(__x86_64__) || defined(__i386__) || defined(_M_X64) || defined(_M_IX86))
    int cpu_info[4] = {0};
    char brand[49] = {0};

    #if defined(_MSC_VER)
        __cpuid(cpu_info, 0x80000000);
    #else
        __asm__ __volatile__("cpuid"
            : "=a"(cpu_info[0]), "=b"(cpu_info[1]), "=c"(cpu_info[2]), "=d"(cpu_info[3])
            : "a"(0x80000000));
    #endif

    unsigned int nExIds = (unsigned int)cpu_info[0];
    if (nExIds >= 0x80000004) {
        for (unsigned int i = 0x80000002; i <= 0x80000004; ++i) {
            #if defined(_MSC_VER)
                __cpuid(cpu_info, i);
            #else
                __asm__ __volatile__("cpuid"
                    : "=a"(cpu_info[0]), "=b"(cpu_info[1]), "=c"(cpu_info[2]), "=d"(cpu_info[3])
                    : "a"(i));
            #endif
            memcpy(brand + (i - 0x80000002) * 16, cpu_info, 16);
        }
        strncpy(out_brand, brand, max_len - 1);
        return;
    }
#endif

#ifdef _WIN32
    strncpy(out_brand, "x86_64 Multi-Core Hardware Processor", max_len - 1);
#elif defined(__aarch64__)
    strncpy(out_brand, "ARM64 High-Performance Mobile SoC Processor", max_len - 1);
#else
    strncpy(out_brand, "Generic Multi-Core System Processor", max_len - 1);
#endif
}
