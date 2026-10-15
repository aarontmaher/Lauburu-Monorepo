import Foundation
import Darwin

public final class DaemonManager {
    public static let shared = DaemonManager()

    private let pidFilePath: String
    private var isRunning: Bool = false
    private var lastHash: String? = nil
    private var lastAppTitle: String? = nil

    private init() {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        let dir = "\(home)/.lauburu"
        try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
        self.pidFilePath = "\(dir)/screen_lens.pid"
    }

    public func isDaemonRunning() -> (Bool, pid_t?) {
        guard let pidStr = try? String(contentsOfFile: pidFilePath, encoding: .utf8).trimmingCharacters(in: .whitespacesAndNewlines),
              let pid = Int32(pidStr) else {
            return (false, nil)
        }

        // kill(pid, 0) checks if process exists without sending a signal
        if kill(pid, 0) == 0 {
            return (true, pid)
        } else {
            // Stale PID file
            try? FileManager.default.removeItem(atPath: pidFilePath)
            return (false, nil)
        }
    }

    public func writePidFile(pid: pid_t) {
        try? "\(pid)".write(toFile: pidFilePath, atomically: true, encoding: .utf8)
    }

    public func removePidFile() {
        try? FileManager.default.removeItem(atPath: pidFilePath)
    }

    public func stopDaemon() -> Bool {
        let (running, pidOpt) = isDaemonRunning()
        guard running, let pid = pidOpt else {
            print("ℹ️ Screen Lens daemon is not currently running.")
            return true
        }

        print("🛑 Sending termination signal to Screen Lens daemon (PID: \(pid))...")
        kill(pid, SIGTERM)

        // Wait up to 5 seconds for daemon to exit
        for _ in 0..<25 {
            usleep(200_000)
            if kill(pid, 0) != 0 {
                removePidFile()
                print("✅ Screen Lens daemon (PID: \(pid)) stopped successfully.")
                return true
            }
        }

        print("⚠️ Force killing daemon (PID: \(pid))...")
        kill(pid, SIGKILL)
        removePidFile()
        return true
    }

    public func launchBackgroundProcess(port: UInt16, interval: Double, mode: OCRMode) {
        let (running, existingPid) = isDaemonRunning()
        if running, let pid = existingPid {
            print("⚠️ Screen Lens daemon is already running (PID: \(pid)) on port \(port).")
            return
        }

        let execPath = CommandLine.arguments[0]
        let process = Process()
        process.executableURL = URL(fileURLWithPath: execPath)
        process.arguments = [
            "start",
            "--port", "\(port)",
            "--interval", "\(interval)",
            "--mode", mode.rawValue,
            "--foreground"
        ]

        let devNull = FileHandle.nullDevice
        process.standardOutput = devNull
        process.standardError = devNull
        process.standardInput = devNull

        do {
            try process.run()
            let pid = process.processIdentifier
            writePidFile(pid: pid)
            print("🚀 Screen Lens daemon launched in background (PID: \(pid)) on port \(port).")
            print("   HTTP API : http://127.0.0.1:\(port)")
            print("   PID File : \(pidFilePath)")
        } catch {
            print("❌ Failed to launch Screen Lens daemon: \(error)")
        }
    }

    public func runForegroundLoop(port: UInt16, interval: Double, mode: OCRMode) async {
        let currentPid = getpid()
        writePidFile(pid: currentPid)

        let server = HttpServer(port: port)
        do {
            try server.start()
        } catch {
            print("❌ Failed to start HTTP server on port \(port): \(error)")
            removePidFile()
            exit(1)
        }

        isRunning = true
        server.updateLoopState(running: true, interval: interval, mode: mode)

        // Signal handlers for graceful termination
        signal(SIGINT, SIG_IGN)
        signal(SIGTERM, SIG_IGN)

        let sigintSource = DispatchSource.makeSignalSource(signal: SIGINT, queue: .main)
        sigintSource.setEventHandler { [weak self] in
            print("\n🛑 Received SIGINT. Shutting down Screen Lens...")
            self?.isRunning = false
            server.stop()
            self?.removePidFile()
            exit(0)
        }
        sigintSource.resume()

        let sigtermSource = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
        sigtermSource.setEventHandler { [weak self] in
            print("\n🛑 Received SIGTERM. Shutting down Screen Lens...")
            self?.isRunning = false
            server.stop()
            self?.removePidFile()
            exit(0)
        }
        sigtermSource.resume()

        // Deduplication stats
        var skippedDuplicates = 0
        var totalCaptures = 0

        print("🔍 Screen Lens capture loop active (\(mode.rawValue) mode, interval: \(interval)s)...")

        while isRunning {
            totalCaptures += 1
            do {
                let snap = try await CaptureEngine.shared.captureMainDisplay()
                let appMeta = WindowInspector.shared.getFrontmostApp()
                let currentAppTitle = "\(appMeta.appName)::\(appMeta.windowTitle)"

                // Enhanced deduplication: exact hash match OR hamming distance <= 3
                var isDuplicate = false
                if let prevHash = lastHash {
                    let exactMatch = snap.perceptualHash == prevHash
                    let hammingDist = CaptureEngine.shared.hammingDistance(hash1: snap.perceptualHash, hash2: prevHash)
                    let nearDuplicate = hammingDist <= 3
                    let sameWindow = currentAppTitle == lastAppTitle

                    if (exactMatch || nearDuplicate) && sameWindow {
                        isDuplicate = true
                        skippedDuplicates += 1
                        // Log dedup stats every 100 captures
                        if totalCaptures % 100 == 0 {
                            let pct = Double(skippedDuplicates) / Double(totalCaptures) * 100.0
                            print(String(format: "📊 Dedup stats: %d/%d skipped (%.1f%%)", skippedDuplicates, totalCaptures, pct))
                        }
                    }
                }

                if isDuplicate {
                    // Screen has not meaningfully changed; skip heavy OCR to conserve ANE/GPU compute
                } else {
                    let ocr = VisionOCR.shared.recognizeText(
                        from: snap.cgImage,
                        mode: mode,
                        screenWidth: snap.width,
                        screenHeight: snap.height
                    )

                    let capId = DatabaseManager.shared.insertCapture(
                        snapshot: snap,
                        appMeta: appMeta,
                        ocrResult: ocr
                    )

                    self.lastHash = snap.perceptualHash
                    self.lastAppTitle = currentAppTitle

                    // SSE Broadcast
                    let ssePayload = "{\"id\":\(capId),\"app\":\"\(appMeta.appName)\",\"blocks\":\(ocr.textBlocks.count),\"dur_ms\":\(snap.captureDurationMs + ocr.durationMs)}"
                    server.broadcastSSE(event: "capture", data: ssePayload)
                }
            } catch {
                // Log and continue on transient capture failures
            }

            try? await Task.sleep(nanoseconds: UInt64(interval * 1_000_000_000))
        }

        server.stop()
        removePidFile()
    }
}
