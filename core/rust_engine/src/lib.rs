// ==============================================================================
// Roblox Multi-Tag Network Controller - Rust Native Hardware Engine
// High-Precision Memory-Safe Machine Code Introspection (Rust + ASM + C ABI)
// ==============================================================================

use std::ffi::CStr;
use std::os::raw::{c_char, c_int};

/// Đọc trực tiếp thanh ghi Assembly Time Stamp Counter (RDTSC / ARM64 CNTVCT_EL0)
#[no_mangle]
pub extern "C" fn rust_read_hardware_tsc() -> u64 {
    #[cfg(target_arch = "x86_64")]
    unsafe {
        core::arch::x86_64::_rdtsc()
    }
    #[cfg(target_arch = "x86")]
    unsafe {
        core::arch::x86::_rdtsc()
    }
    #[cfg(target_arch = "aarch64")]
    unsafe {
        let mut val: u64;
        std::arch::asm!("mrs {}, cntvct_el0", out(reg) val);
        val
    }
    #[cfg(not(any(target_arch = "x86_64", target_arch = "x86", target_arch = "aarch64")))]
    {
        use std::time::{SystemTime, UNIX_EPOCH};
        SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_nanos() as u64
    }
}

/// Đo lường tỷ lệ sử dụng CPU thời gian thực qua Rust
#[no_mangle]
pub extern "C" fn rust_get_cpu_usage(cpu_pct: *mut f64, tsc_counter: *mut u64) -> c_int {
    if !tsc_counter.is_null() {
        unsafe { *tsc_counter = rust_read_hardware_tsc(); }
    }

    #[cfg(target_os = "windows")]
    {
        use std::mem::zeroed;
        #[repr(C)]
        struct FILETIME {
            dw_low_date_time: u32,
            dw_high_date_time: u32,
        }

        extern "system" {
            fn GetSystemTimes(
                lp_idle_time: *mut FILETIME,
                lp_kernel_time: *mut FILETIME,
                lp_user_time: *mut FILETIME,
            ) -> i32;
        }

        unsafe {
            let mut idle: FILETIME = zeroed();
            let mut kernel: FILETIME = zeroed();
            let mut user: FILETIME = zeroed();

            if GetSystemTimes(&mut idle, &mut kernel, &mut user) != 0 {
                let cur_idle = ((idle.dw_high_date_time as u64) << 32) | (idle.dw_low_date_time as u64);
                let cur_kernel = ((kernel.dw_high_date_time as u64) << 32) | (kernel.dw_low_date_time as u64);
                let cur_user = ((user.dw_high_date_time as u64) << 32) | (user.dw_low_date_time as u64);
                let total = cur_kernel + cur_user;

                if total > 0 && !cpu_pct.is_null() {
                    let usage = (1.0 - (cur_idle as f64 / total as f64)) * 100.0;
                    *cpu_pct = usage.clamp(0.0, 100.0);
                    return 0;
                }
            }
        }
    }

    #[cfg(target_os = "linux")]
    {
        use std::fs::File;
        use std::io::{BufRead, BufReader};

        if let Ok(file) = File::open("/proc/stat") {
            let mut reader = BufReader::new(file);
            let mut line = String::new();
            if reader.read_line(&mut line).is_ok() {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if parts.len() >= 5 {
                    let user: u64 = parts[1].parse().unwrap_or(0);
                    let nice: u64 = parts[2].parse().unwrap_or(0);
                    let system: u64 = parts[3].parse().unwrap_or(0);
                    let idle: u64 = parts[4].parse().unwrap_or(0);
                    let iowait: u64 = if parts.len() > 5 { parts[5].parse().unwrap_or(0) } else { 0 };
                    let irq: u64 = if parts.len() > 6 { parts[6].parse().unwrap_or(0) } else { 0 };
                    let softirq: u64 = if parts.len() > 7 { parts[7].parse().unwrap_or(0) } else { 0 };
                    let steal: u64 = if parts.len() > 8 { parts[8].parse().unwrap_or(0) } else { 0 };

                    let cur_idle = idle + iowait;
                    let total = user + nice + system + idle + iowait + irq + softirq + steal;

                    if total > 0 && !cpu_pct.is_null() {
                        let usage = (1.0 - (cur_idle as f64 / total as f64)) * 100.0;
                        unsafe { *cpu_pct = usage.clamp(0.0, 100.0); }
                        return 0;
                    }
                }
            }
        }
    }

    -1
}

/// Đo lường RAM máy tính chính xác từng Byte qua Rust
#[no_mangle]
pub extern "C" fn rust_get_ram_info(
    total_bytes: *mut u64,
    avail_bytes: *mut u64,
    used_bytes: *mut u64,
    percent: *mut f64,
) -> c_int {
    #[cfg(target_os = "windows")]
    {
        use std::mem::{size_of, zeroed};

        #[repr(C)]
        struct MEMORYSTATUSEX {
            dw_length: u32,
            dw_memory_load: u32,
            ull_total_phys: u64,
            ull_avail_phys: u64,
            ull_total_page_file: u64,
            ull_avail_page_file: u64,
            ull_total_virtual: u64,
            ull_avail_virtual: u64,
            ull_avail_extended_virtual: u64,
        }

        extern "system" {
            fn GlobalMemoryStatusEx(lp_buffer: *mut MEMORYSTATUSEX) -> i32;
        }

        unsafe {
            let mut mem: MEMORYSTATUSEX = zeroed();
            mem.dw_length = size_of::<MEMORYSTATUSEX>() as u32;
            if GlobalMemoryStatusEx(&mut mem) != 0 {
                let total = mem.ull_total_phys;
                let avail = mem.ull_avail_phys;
                let used = if total > avail { total - avail } else { 0 };
                let pct = if total > 0 { (used as f64 / total as f64) * 100.0 } else { mem.dw_memory_load as f64 };

                if !total_bytes.is_null() { *total_bytes = total; }
                if !avail_bytes.is_null() { *avail_bytes = avail; }
                if !used_bytes.is_null()  { *used_bytes  = used; }
                if !percent.is_null()     { *percent     = pct; }
                return 0;
            }
        }
    }

    #[cfg(target_os = "linux")]
    {
        use std::fs::File;
        use std::io::{BufRead, BufReader};

        if let Ok(file) = File::open("/proc/meminfo") {
            let reader = BufReader::new(file);
            let mut total_kb: u64 = 0;
            let mut avail_kb: u64 = 0;

            for line_res in reader.lines() {
                if let Ok(line) = line_res {
                    if line.starts_with("MemTotal:") {
                        if let Some(val_str) = line.split_whitespace().nth(1) {
                            total_kb = val_str.parse().unwrap_or(0);
                        }
                    } else if line.starts_with("MemAvailable:") {
                        if let Some(val_str) = line.split_whitespace().nth(1) {
                            avail_kb = val_str.parse().unwrap_or(0);
                        }
                    }
                }
            }

            if total_kb > 0 {
                let total = total_kb * 1024;
                let avail = avail_kb * 1024;
                let used = if total > avail { total - avail } else { 0 };
                let pct = (used as f64 / total as f64) * 100.0;

                unsafe {
                    if !total_bytes.is_null() { *total_bytes = total; }
                    if !avail_bytes.is_null() { *avail_bytes = avail; }
                    if !used_bytes.is_null()  { *used_bytes  = used; }
                    if !percent.is_null()     { *percent     = pct; }
                }
                return 0;
            }
        }
    }

    -1
}

/// Đo lường dung lượng Ổ cứng chính xác từng Sector qua Rust
#[no_mangle]
pub extern "C" fn rust_get_disk_info(
    mount_path: *const c_char,
    total_bytes: *mut u64,
    free_bytes: *mut u64,
    used_bytes: *mut u64,
    percent: *mut f64,
) -> c_int {
    let path_str = if mount_path.is_null() {
        "C:\\"
    } else {
        unsafe {
            CStr::from_ptr(mount_path).to_str().unwrap_or("C:\\")
        }
    };

    #[cfg(target_os = "windows")]
    {
        use std::ffi::OsStr;
        use std::os::windows::ffi::OsStrExt;

        extern "system" {
            fn GetDiskFreeSpaceExW(
                lp_directory_name: *const u16,
                lp_free_bytes_available: *mut u64,
                lp_total_number_of_bytes: *mut u64,
                lp_total_number_of_free_bytes: *mut u64,
            ) -> i32;
        }

        let wide_path: Vec<u16> = OsStr::new(path_str).encode_wide().chain(std::iter::once(0)).collect();
        let mut free_avail: u64 = 0;
        let mut total: u64 = 0;
        let mut total_free: u64 = 0;

        unsafe {
            if GetDiskFreeSpaceExW(wide_path.as_ptr(), &mut free_avail, &mut total, &mut total_free) != 0 {
                let used = if total > free_avail { total - free_avail } else { 0 };
                let pct = if total > 0 { (used as f64 / total as f64) * 100.0 } else { 0.0 };

                if !total_bytes.is_null() { *total_bytes = total; }
                if !free_bytes.is_null()  { *free_bytes  = free_avail; }
                if !used_bytes.is_null()  { *used_bytes  = used; }
                if !percent.is_null()     { *percent     = pct; }
                return 0;
            }
        }
    }

    #[cfg(target_os = "linux")]
    {
        // Trên Android / Linux POSIX
        let c_path = std::ffi::CString::new(path_str).unwrap_or_default();
        let mut stat: libc::statvfs = unsafe { std::mem::zeroed() };
        if unsafe { libc::statvfs(c_path.as_ptr(), &mut stat) } == 0 {
            let total = stat.f_blocks as u64 * stat.f_frsize as u64;
            let free_b = stat.f_bavail as u64 * stat.f_frsize as u64;
            let used = if total > free_b { total - free_b } else { 0 };
            let pct = if total > 0 { (used as f64 / total as f64) * 100.0 } else { 0.0 };

            unsafe {
                if !total_bytes.is_null() { *total_bytes = total; }
                if !free_bytes.is_null()  { *free_bytes  = free_b; }
                if !used_bytes.is_null()  { *used_bytes  = used; }
                if !percent.is_null()     { *percent     = pct; }
            }
            return 0;
        }
    }

    -1
}
