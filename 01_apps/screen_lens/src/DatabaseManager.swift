import Foundation
import SQLite3

public struct CaptureRecord: Codable {
    public let id: Int64
    public let timestamp: String
    public let unixTsMs: Int64
    public let displayId: Int
    public let screenWidth: Int
    public let screenHeight: Int
    public let activeAppName: String?
    public let activeBundleId: String?
    public let activeWindowTitle: String?
    public let activePid: Int?
    public let rawTextSummary: String
    public let ocrConfidenceAvg: Double
    public let ocrMode: String
    public let captureDurationMs: Double
    public let ocrDurationMs: Double
    public let changeHash: String?

    public init(id: Int64, timestamp: String, unixTsMs: Int64, displayId: Int, screenWidth: Int, screenHeight: Int, activeAppName: String?, activeBundleId: String?, activeWindowTitle: String?, activePid: Int?, rawTextSummary: String, ocrConfidenceAvg: Double, ocrMode: String, captureDurationMs: Double, ocrDurationMs: Double, changeHash: String?) {
        self.id = id
        self.timestamp = timestamp
        self.unixTsMs = unixTsMs
        self.displayId = displayId
        self.screenWidth = screenWidth
        self.screenHeight = screenHeight
        self.activeAppName = activeAppName
        self.activeBundleId = activeBundleId
        self.activeWindowTitle = activeWindowTitle
        self.activePid = activePid
        self.rawTextSummary = rawTextSummary
        self.ocrConfidenceAvg = ocrConfidenceAvg
        self.ocrMode = ocrMode
        self.captureDurationMs = captureDurationMs
        self.ocrDurationMs = ocrDurationMs
        self.changeHash = changeHash
    }
}

public struct SearchResultItem: Codable {
    public let id: Int64
    public let timestamp: String
    public let unixTsMs: Int64
    public let activeAppName: String?
    public let activeWindowTitle: String?
    public let rawTextSummary: String
    public let snippet: String
    public let confidenceAvg: Double
    public let ocrMode: String

    public init(id: Int64, timestamp: String, unixTsMs: Int64, activeAppName: String?, activeWindowTitle: String?, rawTextSummary: String, snippet: String, confidenceAvg: Double, ocrMode: String) {
        self.id = id
        self.timestamp = timestamp
        self.unixTsMs = unixTsMs
        self.activeAppName = activeAppName
        self.activeWindowTitle = activeWindowTitle
        self.rawTextSummary = rawTextSummary
        self.snippet = snippet
        self.confidenceAvg = confidenceAvg
        self.ocrMode = ocrMode
    }
}

public struct QueryResult: Codable {
    public let query: String
    public let total: Int
    public let results: [SearchResultItem]

    public init(query: String, total: Int, results: [SearchResultItem]) {
        self.query = query
        self.total = total
        self.results = results
    }
}

public final class DatabaseManager {
    public static let shared = DatabaseManager()

    private var db: OpaquePointer?
    private let dbQueue = DispatchQueue(label: "lauburu.screen_lens.db", qos: .userInitiated)
    private let dbPath: String

    public init(customPath: String? = nil) {
        if let custom = customPath {
            self.dbPath = custom
        } else {
            let home = FileManager.default.homeDirectoryForCurrentUser.path
            let dir = "\(home)/.lauburu"
            try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
            self.dbPath = "\(dir)/screen_lens.sqlite"
        }
        openDatabase()
        initializeSchema()
    }

    deinit {
        closeDatabase()
    }

    private func openDatabase() {
        if sqlite3_open_v2(dbPath, &db, SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_OPEN_FULLMUTEX, nil) != SQLITE_OK {
            print("❌ Failed to open database at \(dbPath)")
        }
    }

    private func closeDatabase() {
        if let d = db {
            sqlite3_close_v2(d)
            db = nil
        }
    }

    private func initializeSchema() {
        dbQueue.sync {
            guard let db = self.db else { return }

            sqlite3_exec(db, "PRAGMA journal_mode = WAL;", nil, nil, nil)
            sqlite3_exec(db, "PRAGMA synchronous = NORMAL;", nil, nil, nil)
            sqlite3_exec(db, "PRAGMA foreign_keys = ON;", nil, nil, nil)

            let createCapturesTable = """
            CREATE TABLE IF NOT EXISTS captures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                unix_ts_ms INTEGER NOT NULL,
                display_id INTEGER NOT NULL DEFAULT 0,
                screen_width INTEGER NOT NULL,
                screen_height INTEGER NOT NULL,
                active_app_name TEXT,
                active_bundle_id TEXT,
                active_window_title TEXT,
                active_pid INTEGER,
                raw_text_summary TEXT NOT NULL,
                ocr_confidence_avg REAL NOT NULL,
                ocr_mode TEXT NOT NULL,
                capture_duration_ms REAL NOT NULL,
                ocr_duration_ms REAL NOT NULL,
                change_hash TEXT
            );
            """
            sqlite3_exec(db, createCapturesTable, nil, nil, nil)

            let createBlocksTable = """
            CREATE TABLE IF NOT EXISTS ocr_text_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capture_id INTEGER NOT NULL,
                block_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                confidence REAL NOT NULL,
                bbox_x REAL NOT NULL,
                bbox_y REAL NOT NULL,
                bbox_w REAL NOT NULL,
                bbox_h REAL NOT NULL,
                pixel_x INTEGER NOT NULL,
                pixel_y INTEGER NOT NULL,
                pixel_w INTEGER NOT NULL,
                pixel_h INTEGER NOT NULL,
                FOREIGN KEY (capture_id) REFERENCES captures(id) ON DELETE CASCADE
            );
            """
            sqlite3_exec(db, createBlocksTable, nil, nil, nil)

            let createFts = """
            CREATE VIRTUAL TABLE IF NOT EXISTS captures_fts USING fts5(
                raw_text_summary,
                active_app_name,
                active_window_title,
                content='captures',
                content_rowid='id'
            );
            """
            sqlite3_exec(db, createFts, nil, nil, nil)

            let createTriggers = """
            CREATE TRIGGER IF NOT EXISTS captures_ai AFTER INSERT ON captures BEGIN
                INSERT INTO captures_fts(rowid, raw_text_summary, active_app_name, active_window_title)
                VALUES (new.id, new.raw_text_summary, new.active_app_name, new.active_window_title);
            END;

            CREATE TRIGGER IF NOT EXISTS captures_ad AFTER DELETE ON captures BEGIN
                INSERT INTO captures_fts(captures_fts, rowid, raw_text_summary, active_app_name, active_window_title)
                VALUES ('delete', old.id, old.raw_text_summary, old.active_app_name, old.active_window_title);
            END;
            """
            sqlite3_exec(db, createTriggers, nil, nil, nil)

            let createIndices = """
            CREATE INDEX IF NOT EXISTS idx_captures_unix_ts ON captures(unix_ts_ms);
            CREATE INDEX IF NOT EXISTS idx_captures_app ON captures(active_app_name);
            CREATE INDEX IF NOT EXISTS idx_ocr_blocks_capture_id ON ocr_text_blocks(capture_id);
            """
            sqlite3_exec(db, createIndices, nil, nil, nil)
        }
    }

    public func insertCapture(
        snapshot: CaptureSnapshot,
        appMeta: AppMetadata,
        ocrResult: OCRResult
    ) -> Int64 {
        return dbQueue.sync {
            guard let db = self.db else { return -1 }

            let now = Date()
            let isoFormatter = ISO8601DateFormatter()
            isoFormatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            let isoTimestamp = isoFormatter.string(from: now)
            let unixMs = Int64(now.timeIntervalSince1970 * 1000.0)

            let insertSql = """
            INSERT INTO captures (
                timestamp, unix_ts_ms, display_id, screen_width, screen_height,
                active_app_name, active_bundle_id, active_window_title, active_pid,
                raw_text_summary, ocr_confidence_avg, ocr_mode,
                capture_duration_ms, ocr_duration_ms, change_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """

            var stmt: OpaquePointer?
            if sqlite3_prepare_v2(db, insertSql, -1, &stmt, nil) != SQLITE_OK {
                return -1
            }

            sqlite3_bind_text(stmt, 1, (isoTimestamp as NSString).utf8String, -1, nil)
            sqlite3_bind_int64(stmt, 2, unixMs)
            sqlite3_bind_int(stmt, 3, Int32(snapshot.displayId))
            sqlite3_bind_int(stmt, 4, Int32(snapshot.width))
            sqlite3_bind_int(stmt, 5, Int32(snapshot.height))

            sqlite3_bind_text(stmt, 6, (appMeta.appName as NSString).utf8String, -1, nil)
            if let bid = appMeta.bundleId {
                sqlite3_bind_text(stmt, 7, (bid as NSString).utf8String, -1, nil)
            } else {
                sqlite3_bind_null(stmt, 7)
            }
            sqlite3_bind_text(stmt, 8, (appMeta.windowTitle as NSString).utf8String, -1, nil)
            sqlite3_bind_int(stmt, 9, Int32(appMeta.pid))

            let combinedSummary = appMeta.accessibilitySummary.isEmpty ? ocrResult.fullText : (ocrResult.fullText + "\n[UI Accessibility Tree]:\n" + appMeta.accessibilitySummary)
            sqlite3_bind_text(stmt, 10, (combinedSummary as NSString).utf8String, -1, nil)
            sqlite3_bind_double(stmt, 11, ocrResult.confidenceAvg)
            sqlite3_bind_text(stmt, 12, (ocrResult.mode as NSString).utf8String, -1, nil)
            sqlite3_bind_double(stmt, 13, snapshot.captureDurationMs)
            sqlite3_bind_double(stmt, 14, ocrResult.durationMs)
            sqlite3_bind_text(stmt, 15, (snapshot.perceptualHash as NSString).utf8String, -1, nil)

            if sqlite3_step(stmt) != SQLITE_DONE {
                sqlite3_finalize(stmt)
                return -1
            }
            sqlite3_finalize(stmt)

            let captureId = sqlite3_last_insert_rowid(db)

            // Insert OCR text blocks
            let blockSql = """
            INSERT INTO ocr_text_blocks (
                capture_id, block_index, text, confidence,
                bbox_x, bbox_y, bbox_w, bbox_h,
                pixel_x, pixel_y, pixel_w, pixel_h
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """

            var blockStmt: OpaquePointer?
            if sqlite3_prepare_v2(db, blockSql, -1, &blockStmt, nil) == SQLITE_OK {
                for (idx, block) in ocrResult.textBlocks.enumerated() {
                    sqlite3_bind_int64(blockStmt, 1, captureId)
                    sqlite3_bind_int(blockStmt, 2, Int32(idx))
                    sqlite3_bind_text(blockStmt, 3, (block.text as NSString).utf8String, -1, nil)
                    sqlite3_bind_double(blockStmt, 4, block.confidence)
                    sqlite3_bind_double(blockStmt, 5, block.bboxX)
                    sqlite3_bind_double(blockStmt, 6, block.bboxY)
                    sqlite3_bind_double(blockStmt, 7, block.bboxW)
                    sqlite3_bind_double(blockStmt, 8, block.bboxH)
                    sqlite3_bind_int(blockStmt, 9, Int32(block.pixelX))
                    sqlite3_bind_int(blockStmt, 10, Int32(block.pixelY))
                    sqlite3_bind_int(blockStmt, 11, Int32(block.pixelW))
                    sqlite3_bind_int(blockStmt, 12, Int32(block.pixelH))

                    _ = sqlite3_step(blockStmt)
                    sqlite3_reset(blockStmt)
                }
                sqlite3_finalize(blockStmt)
            }

            return captureId
        }
    }

    public func queryFTS(term: String, app: String? = nil, limit: Int = 20) -> QueryResult {
        return dbQueue.sync {
            guard let db = self.db else { return QueryResult(query: term, total: 0, results: []) }

            var results: [SearchResultItem] = []
            let cleanTerm = term.trimmingCharacters(in: .whitespacesAndNewlines)

            // Try FTS5 MATCH query first
            let ftsSql: String
            if let appFilter = app, !appFilter.isEmpty {
                ftsSql = """
                SELECT c.id, c.timestamp, c.unix_ts_ms, c.active_app_name, c.active_window_title,
                       c.raw_text_summary, snippet(captures_fts, 0, '<b>', '</b>', '...', 15),
                       c.ocr_confidence_avg, c.ocr_mode
                FROM captures_fts f
                JOIN captures c ON f.rowid = c.id
                WHERE captures_fts MATCH ? AND c.active_app_name = ?
                ORDER BY f.rowid DESC
                LIMIT ?;
                """
            } else {
                ftsSql = """
                SELECT c.id, c.timestamp, c.unix_ts_ms, c.active_app_name, c.active_window_title,
                       c.raw_text_summary, snippet(captures_fts, 0, '<b>', '</b>', '...', 15),
                       c.ocr_confidence_avg, c.ocr_mode
                FROM captures_fts f
                JOIN captures c ON f.rowid = c.id
                WHERE captures_fts MATCH ?
                ORDER BY f.rowid DESC
                LIMIT ?;
                """
            }

            var stmt: OpaquePointer?
            let ftsEscaped = cleanTerm.contains("\"") ? cleanTerm : "\"\(cleanTerm)\""

            if sqlite3_prepare_v2(db, ftsSql, -1, &stmt, nil) == SQLITE_OK {
                sqlite3_bind_text(stmt, 1, (ftsEscaped as NSString).utf8String, -1, nil)
                if let appFilter = app, !appFilter.isEmpty {
                    sqlite3_bind_text(stmt, 2, (appFilter as NSString).utf8String, -1, nil)
                    sqlite3_bind_int(stmt, 3, Int32(limit))
                } else {
                    sqlite3_bind_int(stmt, 2, Int32(limit))
                }

                while sqlite3_step(stmt) == SQLITE_ROW {
                    let id = sqlite3_column_int64(stmt, 0)
                    let ts = String(cString: sqlite3_column_text(stmt, 1))
                    let unixTs = sqlite3_column_int64(stmt, 2)
                    let appName = sqlite3_column_text(stmt, 3).map { String(cString: $0) }
                    let winTitle = sqlite3_column_text(stmt, 4).map { String(cString: $0) }
                    let rawSummary = sqlite3_column_text(stmt, 5).map { String(cString: $0) } ?? ""
                    let snip = sqlite3_column_text(stmt, 6).map { String(cString: $0) } ?? ""
                    let conf = sqlite3_column_double(stmt, 7)
                    let mode = sqlite3_column_text(stmt, 8).map { String(cString: $0) } ?? "fast"

                    results.append(SearchResultItem(
                        id: id,
                        timestamp: ts,
                        unixTsMs: unixTs,
                        activeAppName: appName,
                        activeWindowTitle: winTitle,
                        rawTextSummary: rawSummary,
                        snippet: snip.isEmpty ? String(rawSummary.prefix(120)) : snip,
                        confidenceAvg: conf,
                        ocrMode: mode
                    ))
                }
                sqlite3_finalize(stmt)
            }

            // If FTS returned 0 results or had match parsing syntax issues, fallback to LIKE
            if results.isEmpty && !cleanTerm.isEmpty {
                let likePattern = "%\(cleanTerm)%"
                let likeSql: String
                if let appFilter = app, !appFilter.isEmpty {
                    likeSql = """
                    SELECT id, timestamp, unix_ts_ms, active_app_name, active_window_title,
                           raw_text_summary, ocr_confidence_avg, ocr_mode
                    FROM captures
                    WHERE (raw_text_summary LIKE ? OR active_window_title LIKE ?) AND active_app_name = ?
                    ORDER BY unix_ts_ms DESC
                    LIMIT ?;
                    """
                } else {
                    likeSql = """
                    SELECT id, timestamp, unix_ts_ms, active_app_name, active_window_title,
                           raw_text_summary, ocr_confidence_avg, ocr_mode
                    FROM captures
                    WHERE raw_text_summary LIKE ? OR active_window_title LIKE ?
                    ORDER BY unix_ts_ms DESC
                    LIMIT ?;
                    """
                }

                var likeStmt: OpaquePointer?
                if sqlite3_prepare_v2(db, likeSql, -1, &likeStmt, nil) == SQLITE_OK {
                    sqlite3_bind_text(likeStmt, 1, (likePattern as NSString).utf8String, -1, nil)
                    sqlite3_bind_text(likeStmt, 2, (likePattern as NSString).utf8String, -1, nil)
                    if let appFilter = app, !appFilter.isEmpty {
                        sqlite3_bind_text(likeStmt, 3, (appFilter as NSString).utf8String, -1, nil)
                        sqlite3_bind_int(likeStmt, 4, Int32(limit))
                    } else {
                        sqlite3_bind_int(likeStmt, 3, Int32(limit))
                    }

                    while sqlite3_step(likeStmt) == SQLITE_ROW {
                        let id = sqlite3_column_int64(likeStmt, 0)
                        let ts = String(cString: sqlite3_column_text(likeStmt, 1))
                        let unixTs = sqlite3_column_int64(likeStmt, 2)
                        let appName = sqlite3_column_text(likeStmt, 3).map { String(cString: $0) }
                        let winTitle = sqlite3_column_text(likeStmt, 4).map { String(cString: $0) }
                        let rawSummary = sqlite3_column_text(likeStmt, 5).map { String(cString: $0) } ?? ""
                        let conf = sqlite3_column_double(likeStmt, 6)
                        let mode = sqlite3_column_text(likeStmt, 7).map { String(cString: $0) } ?? "fast"

                        results.append(SearchResultItem(
                            id: id,
                            timestamp: ts,
                            unixTsMs: unixTs,
                            activeAppName: appName,
                            activeWindowTitle: winTitle,
                            rawTextSummary: rawSummary,
                            snippet: String(rawSummary.prefix(120)),
                            confidenceAvg: conf,
                            ocrMode: mode
                        ))
                    }
                    sqlite3_finalize(likeStmt)
                }
            }

            return QueryResult(query: term, total: results.count, results: results)
        }
    }

    public func getLatestCapture() -> (CaptureRecord, [OCRTextBlock])? {
        return dbQueue.sync {
            guard let db = self.db else { return nil }

            let sql = """
            SELECT id, timestamp, unix_ts_ms, display_id, screen_width, screen_height,
                   active_app_name, active_bundle_id, active_window_title, active_pid,
                   raw_text_summary, ocr_confidence_avg, ocr_mode,
                   capture_duration_ms, ocr_duration_ms, change_hash
            FROM captures
            ORDER BY unix_ts_ms DESC
            LIMIT 1;
            """

            var stmt: OpaquePointer?
            guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else { return nil }

            guard sqlite3_step(stmt) == SQLITE_ROW else {
                sqlite3_finalize(stmt)
                return nil
            }

            let id = sqlite3_column_int64(stmt, 0)
            let ts = String(cString: sqlite3_column_text(stmt, 1))
            let unixTs = sqlite3_column_int64(stmt, 2)
            let displayId = Int(sqlite3_column_int(stmt, 3))
            let w = Int(sqlite3_column_int(stmt, 4))
            let h = Int(sqlite3_column_int(stmt, 5))
            let appName = sqlite3_column_text(stmt, 6).map { String(cString: $0) }
            let bundleId = sqlite3_column_text(stmt, 7).map { String(cString: $0) }
            let winTitle = sqlite3_column_text(stmt, 8).map { String(cString: $0) }
            let pid = sqlite3_column_type(stmt, 9) != SQLITE_NULL ? Int(sqlite3_column_int(stmt, 9)) : nil
            let rawSummary = sqlite3_column_text(stmt, 10).map { String(cString: $0) } ?? ""
            let conf = sqlite3_column_double(stmt, 11)
            let mode = sqlite3_column_text(stmt, 12).map { String(cString: $0) } ?? "fast"
            let capDur = sqlite3_column_double(stmt, 13)
            let ocrDur = sqlite3_column_double(stmt, 14)
            let hash = sqlite3_column_text(stmt, 15).map { String(cString: $0) }

            sqlite3_finalize(stmt)

            let record = CaptureRecord(
                id: id,
                timestamp: ts,
                unixTsMs: unixTs,
                displayId: displayId,
                screenWidth: w,
                screenHeight: h,
                activeAppName: appName,
                activeBundleId: bundleId,
                activeWindowTitle: winTitle,
                activePid: pid,
                rawTextSummary: rawSummary,
                ocrConfidenceAvg: conf,
                ocrMode: mode,
                captureDurationMs: capDur,
                ocrDurationMs: ocrDur,
                changeHash: hash
            )

            // Fetch blocks
            var blocks: [OCRTextBlock] = []
            let blockSql = """
            SELECT text, confidence, bbox_x, bbox_y, bbox_w, bbox_h, pixel_x, pixel_y, pixel_w, pixel_h
            FROM ocr_text_blocks
            WHERE capture_id = ?
            ORDER BY block_index ASC;
            """
            var bStmt: OpaquePointer?
            if sqlite3_prepare_v2(db, blockSql, -1, &bStmt, nil) == SQLITE_OK {
                sqlite3_bind_int64(bStmt, 1, id)
                while sqlite3_step(bStmt) == SQLITE_ROW {
                    let text = sqlite3_column_text(bStmt, 0).map { String(cString: $0) } ?? ""
                    let bConf = sqlite3_column_double(bStmt, 1)
                    let bx = sqlite3_column_double(bStmt, 2)
                    let by = sqlite3_column_double(bStmt, 3)
                    let bw = sqlite3_column_double(bStmt, 4)
                    let bh = sqlite3_column_double(bStmt, 5)
                    let px = Int(sqlite3_column_int(bStmt, 6))
                    let py = Int(sqlite3_column_int(bStmt, 7))
                    let pw = Int(sqlite3_column_int(bStmt, 8))
                    let ph = Int(sqlite3_column_int(bStmt, 9))

                    blocks.append(OCRTextBlock(
                        text: text,
                        confidence: bConf,
                        bboxX: bx,
                        bboxY: by,
                        bboxW: bw,
                        bboxH: bh,
                        pixelX: px,
                        pixelY: py,
                        pixelW: pw,
                        pixelH: ph
                    ))
                }
                sqlite3_finalize(bStmt)
            }

            return (record, blocks)
        }
    }

    public func getCaptureCount() -> Int {
        return dbQueue.sync {
            guard let db = self.db else { return 0 }
            var stmt: OpaquePointer?
            guard sqlite3_prepare_v2(db, "SELECT count(*) FROM captures;", -1, &stmt, nil) == SQLITE_OK else { return 0 }
            defer { sqlite3_finalize(stmt) }
            if sqlite3_step(stmt) == SQLITE_ROW {
                return Int(sqlite3_column_int(stmt, 0))
            }
            return 0
        }
    }

    public func getDatabaseSizeBytes() -> Int64 {
        do {
            let attrs = try FileManager.default.attributesOfItem(atPath: dbPath)
            return (attrs[.size] as? Int64) ?? 0
        } catch {
            return 0
        }
    }

    public func pruneOldCaptures(days: Int) -> Int {
        return dbQueue.sync {
            guard let db = self.db else { return 0 }
            let cutoffMs = Int64((Date().timeIntervalSince1970 - Double(days * 86400)) * 1000.0)
            
            var stmt: OpaquePointer?
            guard sqlite3_prepare_v2(db, "DELETE FROM captures WHERE unix_ts_ms < ?;", -1, &stmt, nil) == SQLITE_OK else { return 0 }
            sqlite3_bind_int64(stmt, 1, cutoffMs)
            let result = sqlite3_step(stmt)
            sqlite3_finalize(stmt)

            if result == SQLITE_DONE {
                let changes = Int(sqlite3_changes(db))
                return changes
            }
            return 0
        }
    }
}
