// ProcessMonitor — System health monitoring via sysctl/host_statistics
// M3-optimized: uses Darwin APIs directly, no shell exec

import Foundation
import os.log
import Darwin

private let logger = Logger(subsystem: "us.giovannini.foks", category: "ProcessMonitor")

public final class ProcessMonitor {
    private var timer: Timer?

    public init() {}

    public func startMonitoring() {
        timer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { _ in
            let stats = Self.currentStats()
            logger.debug("CPU: \(String(format: "%.1f", stats.cpuUsage))% | Mem: \(String(format: "%.1f", stats.memoryUsedGB))/\(stats.memoryTotalGB)GB")
        }
    }

    public func stopMonitoring() { timer?.invalidate(); timer = nil }

    public static func currentStats() -> SystemStats {
        SystemStats(
            cpuUsage: cpuUsage(),
            memoryUsedGB: memoryUsed(),
            memoryTotalGB: Double(FoKSConfig.memoryGB),
            uptime: ProcessInfo.processInfo.systemUptime,
            activeProcessCount: processCount()
        )
    }

    // MARK: - CPU via host_processor_info
    private static func cpuUsage() -> Double {
        var numCPU: natural_t = 0
        var cpuInfo: processor_info_array_t?
        var cpuInfoCnt: mach_msg_type_number_t = 0

        let result = host_processor_info(
            mach_host_self(), PROCESSOR_CPU_LOAD_INFO,
            &numCPU, &cpuInfo, &cpuInfoCnt
        )
        guard result == KERN_SUCCESS, let info = cpuInfo else { return 0 }
        defer { vm_deallocate(mach_task_self_, vm_address_t(bitPattern: info), vm_size_t(cpuInfoCnt) * vm_size_t(MemoryLayout<integer_t>.size)) }

        var totalUser: Int32 = 0, totalSystem: Int32 = 0, totalIdle: Int32 = 0
        for i in 0..<Int(numCPU) {
            let base = i * Int(CPU_STATE_MAX)
            totalUser += info[base + Int(CPU_STATE_USER)]
            totalSystem += info[base + Int(CPU_STATE_SYSTEM)]
            totalIdle += info[base + Int(CPU_STATE_IDLE)]
        }
        let total = Double(totalUser + totalSystem + totalIdle)
        guard total > 0 else { return 0 }
        return Double(totalUser + totalSystem) / total * 100
    }

    // MARK: - Memory via host_statistics64
    private static func memoryUsed() -> Double {
        var stats = vm_statistics64()
        var count = mach_msg_type_number_t(MemoryLayout<vm_statistics64>.size / MemoryLayout<integer_t>.size)
        let result = withUnsafeMutablePointer(to: &stats) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                host_statistics64(mach_host_self(), HOST_VM_INFO64, $0, &count)
            }
        }
        guard result == KERN_SUCCESS else { return 0 }
        let pageSize = Double(vm_kernel_page_size)
        let active = Double(stats.active_count) * pageSize
        let wired = Double(stats.wire_count) * pageSize
        let compressed = Double(stats.compressor_page_count) * pageSize
        return (active + wired + compressed) / 1_073_741_824 // bytes to GB
    }

    private static func processCount() -> Int {
        var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_ALL, 0]
        var size: size_t = 0
        sysctl(&mib, UInt32(mib.count), nil, &size, nil, 0)
        return size / MemoryLayout<kinfo_proc>.size
    }
}
