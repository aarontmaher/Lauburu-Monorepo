import Foundation
import AppKit

func printUsage() {
    let usage = """
    ======================================================================
    🔍 LAUBURU SCREEN LENS (lauburu-lens) — Native macOS Vision Daemon & CLI
    ======================================================================
    Usage: lauburu-lens <command> [options]

    Commands:
      start              Start the screen capture loop and HTTP API server (:3035)
                         Options:
                           --port <int>         HTTP server port (default: 3035)
                           --interval <float>   Capture interval in seconds (default: 2.0)
                           --mode <fast|accurate> OCR recognition mode (default: fast)
                           --daemon             Run in background daemon mode
                           --foreground         Run in current terminal session

      stop               Stop running Screen Lens background daemon

      status             Display daemon health, capture metrics & DB statistics
                         Options:
                           --json               Output status in JSON format

      capture            Trigger immediate on-demand display capture + OCR
                         Options:
                           --mode <fast|accurate> OCR recognition mode (default: fast)
                           --json               Output captured metadata in JSON format
                           --no-save            Do not persist capture to SQLite

      query <text>       Search captured text records using SQLite FTS5 full-text search
                         Options:
                           --app <name>         Filter results by application name
                           --limit <int>        Maximum number of results (default: 20)
                           --json               Output results in JSON format

      windows            List all active on-screen windows and application bounds
                         Options:
                           --json               Output window list in JSON format

      prune              Prune historical capture records older than N days
                         Options:
                           --days <int>         Retention threshold in days (default: 7)

      help               Display this help message
    ======================================================================
    """
    print(usage)
}

func parseFlagValue(args: [String], flag: String) -> String? {
    for i in 0..<args.count {
        if args[i] == flag && i + 1 < args.count {
            return args[i + 1]
        }
    }
    return nil
}

func hasFlag(args: [String], flag: String) -> Bool {
    return args.contains(flag)
}

@main
struct ScreenLensCLI {
    static func main() async {
        let args = Array(CommandLine.arguments.dropFirst())
        guard let command = args.first else {
            printUsage()
            exit(0)
        }

        let cmdArgs = Array(args.dropFirst())

        switch command.lowercased() {
        case "start":
            let portStr = parseFlagValue(args: cmdArgs, flag: "--port") ?? "3035"
            let port = UInt16(portStr) ?? 3035
            let intervalStr = parseFlagValue(args: cmdArgs, flag: "--interval") ?? "2.0"
            let interval = Double(intervalStr) ?? 2.0
            let modeStr = parseFlagValue(args: cmdArgs, flag: "--mode") ?? "fast"
            let mode = (modeStr == "accurate") ? OCRMode.accurate : OCRMode.fast
            let isDaemon = hasFlag(args: cmdArgs, flag: "--daemon")
            let isForeground = hasFlag(args: cmdArgs, flag: "--foreground")

            if isDaemon && !isForeground {
                DaemonManager.shared.launchBackgroundProcess(port: port, interval: interval, mode: mode)
            } else {
                await DaemonManager.shared.runForegroundLoop(port: port, interval: interval, mode: mode)
            }

        case "stop":
            _ = DaemonManager.shared.stopDaemon()

        case "status":
            let isJson = hasFlag(args: cmdArgs, flag: "--json")
            let (running, pid) = DaemonManager.shared.isDaemonRunning()
            let db = DatabaseManager.shared
            let count = db.getCaptureCount()
            let sizeBytes = db.getDatabaseSizeBytes()
            let sizeMb = Double(sizeBytes) / (1024.0 * 1024.0)
            let frontApp = WindowInspector.shared.getFrontmostApp()

            if isJson {
                let statusDict: [String: Any] = [
                    "daemon_running": running,
                    "pid": pid ?? 0,
                    "total_captures": count,
                    "db_size_bytes": sizeBytes,
                    "db_size_mb": sizeMb,
                    "front_app": frontApp.appName,
                    "front_window": frontApp.windowTitle,
                    "front_bundle_id": frontApp.bundleId ?? ""
                ]
                if let jsonData = try? JSONSerialization.data(withJSONObject: statusDict, options: [.prettyPrinted, .sortedKeys]),
                   let jsonStr = String(data: jsonData, encoding: .utf8) {
                    print(jsonStr)
                }
            } else {
                print("======================================================================")
                print("🔍 LAUBURU SCREEN LENS STATUS")
                print("======================================================================")
                print("Daemon Status   : \(running ? "🟢 ACTIVE (PID: \(pid ?? 0))" : "⚪ STOPPED")")
                print("Database Records: \(count) captures")
                print("Database Size   : \(String(format: "%.2f MB", sizeMb)) (~/.lauburu/screen_lens.sqlite)")
                print("Frontmost App   : \(frontApp.appName) (PID: \(frontApp.pid))")
                print("Window Title    : \(frontApp.windowTitle.isEmpty ? "(none)" : frontApp.windowTitle)")
                if let bid = frontApp.bundleId {
                    print("Bundle ID       : \(bid)")
                }
                print("======================================================================")
            }

        case "capture":
            let modeStr = parseFlagValue(args: cmdArgs, flag: "--mode") ?? "fast"
            let mode = (modeStr == "accurate") ? OCRMode.accurate : OCRMode.fast
            let isJson = hasFlag(args: cmdArgs, flag: "--json")
            let noSave = hasFlag(args: cmdArgs, flag: "--no-save")

            do {
                let snap = try await CaptureEngine.shared.captureMainDisplay()
                let appMeta = WindowInspector.shared.getFrontmostApp()
                let ocr = VisionOCR.shared.recognizeText(
                    from: snap.cgImage,
                    mode: mode,
                    screenWidth: snap.width,
                    screenHeight: snap.height
                )

                var capId: Int64 = -1
                if !noSave {
                    capId = DatabaseManager.shared.insertCapture(
                        snapshot: snap,
                        appMeta: appMeta,
                        ocrResult: ocr
                    )
                }

                if isJson {
                    var blockDicts: [[String: Any]] = []
                    for b in ocr.textBlocks {
                        blockDicts.append([
                            "text": b.text,
                            "confidence": b.confidence,
                            "bbox": ["x": b.bboxX, "y": b.bboxY, "w": b.bboxW, "h": b.bboxH],
                            "pixel": ["x": b.pixelX, "y": b.pixelY, "w": b.pixelW, "h": b.pixelH]
                        ])
                    }

                    let isoFormatter = ISO8601DateFormatter()
                    let resultDict: [String: Any] = [
                        "id": capId,
                        "timestamp": isoFormatter.string(from: Date()),
                        "app": appMeta.appName,
                        "window_title": appMeta.windowTitle,
                        "bundle_id": appMeta.bundleId ?? "",
                        "display_id": snap.displayId,
                        "width": snap.width,
                        "height": snap.height,
                        "capture_duration_ms": snap.captureDurationMs,
                        "ocr_duration_ms": ocr.durationMs,
                        "confidence_avg": ocr.confidenceAvg,
                        "mode": mode.rawValue,
                        "text_count": ocr.textBlocks.count,
                        "text_summary": ocr.fullText,
                        "text_blocks": blockDicts
                    ]

                    if let jsonData = try? JSONSerialization.data(withJSONObject: resultDict, options: [.prettyPrinted, .sortedKeys]),
                       let jsonStr = String(data: jsonData, encoding: .utf8) {
                        print(jsonStr)
                    }
                } else {
                    print("======================================================================")
                    print("📸 SCREEN CAPTURE COMPLETED")
                    print("======================================================================")
                    if capId > 0 {
                        print("Record ID       : #\(capId)")
                    }
                    print("Resolution      : \(snap.width)x\(snap.height) (Display \(snap.displayId))")
                    print("Active App      : \(appMeta.appName) (Title: \(appMeta.windowTitle.isEmpty ? "(none)" : appMeta.windowTitle))")
                    print("Latencies       : Frame: \(String(format: "%.1f ms", snap.captureDurationMs)), OCR: \(String(format: "%.1f ms", ocr.durationMs))")
                    print("OCR Results     : \(ocr.textBlocks.count) text regions (Confidence: \(String(format: "%.1f%%", ocr.confidenceAvg * 100)))")
                    print("----------------------------------------------------------------------")
                    print("Preview Text:")
                    let lines = ocr.fullText.components(separatedBy: "\n")
                    for line in lines.prefix(10) {
                        print("  • \(line)")
                    }
                    if lines.count > 10 {
                        print("  ... (\(lines.count - 10) more lines)")
                    }
                    print("======================================================================")
                }
            } catch {
                print("❌ Capture failed: \(error.localizedDescription)")
                exit(1)
            }

        case "query":
            guard let searchTerm = cmdArgs.first, !searchTerm.hasPrefix("--") else {
                print("❌ Error: Query text parameter required. Example: lauburu-lens query \"Terminal\"")
                exit(1)
            }

            let appFilter = parseFlagValue(args: cmdArgs, flag: "--app")
            let limitStr = parseFlagValue(args: cmdArgs, flag: "--limit") ?? "20"
            let limit = Int(limitStr) ?? 20
            let isJson = hasFlag(args: cmdArgs, flag: "--json")

            let queryResult = DatabaseManager.shared.queryFTS(term: searchTerm, app: appFilter, limit: limit)

            if isJson {
                var itemDicts: [[String: Any]] = []
                for item in queryResult.results {
                    itemDicts.append([
                        "id": item.id,
                        "timestamp": item.timestamp,
                        "unix_ts_ms": item.unixTsMs,
                        "app": item.activeAppName ?? "",
                        "window_title": item.activeWindowTitle ?? "",
                        "snippet": item.snippet,
                        "raw_text": item.rawTextSummary,
                        "confidence_avg": item.confidenceAvg,
                        "mode": item.ocrMode
                    ])
                }
                let outDict: [String: Any] = [
                    "query": queryResult.query,
                    "total": queryResult.total,
                    "results": itemDicts
                ]
                if let jsonData = try? JSONSerialization.data(withJSONObject: outDict, options: [.prettyPrinted, .sortedKeys]),
                   let jsonStr = String(data: jsonData, encoding: .utf8) {
                    print(jsonStr)
                }
            } else {
                print("======================================================================")
                print("🔎 SEARCH RESULTS FOR: \"\(searchTerm)\" (Found: \(queryResult.total))")
                print("======================================================================")
                if queryResult.results.isEmpty {
                    print("No matching captures found in database.")
                } else {
                    for r in queryResult.results {
                        print("• [ID #\(r.id)] [\(r.timestamp)] [\(r.activeAppName ?? "App")] \(r.activeWindowTitle ?? "")")
                        print("  Snippet: \(r.snippet.replacingOccurrences(of: "\n", with: " "))")
                        print("----------------------------------------------------------------------")
                    }
                }
            }

        case "windows":
            let isJson = hasFlag(args: cmdArgs, flag: "--json")
            let windows = WindowInspector.shared.getOnScreenWindows()

            if isJson {
                var winDicts: [[String: Any]] = []
                for w in windows {
                    winDicts.append([
                        "id": w.id,
                        "app": w.appName,
                        "title": w.title,
                        "bundle_id": w.bundleId ?? "",
                        "pid": w.pid,
                        "bounds": w.bounds,
                        "layer": w.layer,
                        "on_screen": w.isOnScreen
                    ])
                }
                if let jsonData = try? JSONSerialization.data(withJSONObject: ["count": winDicts.count, "windows": winDicts], options: [.prettyPrinted, .sortedKeys]),
                   let jsonStr = String(data: jsonData, encoding: .utf8) {
                    print(jsonStr)
                }
            } else {
                print("======================================================================")
                print("🪟 ACTIVE ON-SCREEN WINDOWS (Count: \(windows.count))")
                print("======================================================================")
                for w in windows {
                    let b = w.bounds
                    let boundsStr = "\(Int(b["x"] ?? 0)),\(Int(b["y"] ?? 0)) [\(Int(b["w"] ?? 0))x\(Int(b["h"] ?? 0))]"
                    print("• [ID: \(w.id)] [PID: \(w.pid)] \(w.appName): \"\(w.title.isEmpty ? "(untitled)" : w.title)\" -> Bounds: \(boundsStr)")
                }
                print("======================================================================")
            }

        case "prune":
            let daysStr = parseFlagValue(args: cmdArgs, flag: "--days") ?? "7"
            let days = Int(daysStr) ?? 7
            let deleted = DatabaseManager.shared.pruneOldCaptures(days: days)
            print("🧹 Pruned \(deleted) records older than \(days) days from screen_lens.sqlite.")

        case "help", "--help", "-h":
            printUsage()

        default:
            print("❌ Unknown command: \(command)")
            printUsage()
            exit(1)
        }
    }
}
