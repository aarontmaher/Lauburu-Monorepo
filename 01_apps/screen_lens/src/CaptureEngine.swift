import Foundation
import ScreenCaptureKit
import CoreGraphics
import CoreVideo

public struct CaptureSnapshot {
    public let cgImage: CGImage
    public let width: Int
    public let height: Int
    public let displayId: Int
    public let captureDurationMs: Double
    public let perceptualHash: String

    public init(cgImage: CGImage, width: Int, height: Int, displayId: Int, captureDurationMs: Double, perceptualHash: String) {
        self.cgImage = cgImage
        self.width = width
        self.height = height
        self.displayId = displayId
        self.captureDurationMs = captureDurationMs
        self.perceptualHash = perceptualHash
    }
}

public final class CaptureEngine {
    public static let shared = CaptureEngine()

    private init() {}

    public func captureMainDisplay() async throws -> CaptureSnapshot {
        let startTime = CFAbsoluteTimeGetCurrent()
        
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
        guard let display = content.displays.first else {
            throw NSError(domain: "CaptureEngine", code: 1, userInfo: [NSLocalizedDescriptionKey: "No active display found"])
        }

        let filter = SCContentFilter(display: display, excludingWindows: [])
        let config = SCStreamConfiguration()
        config.width = display.width
        config.height = display.height
        config.showsCursor = false
        config.pixelFormat = kCVPixelFormatType_32BGRA

        let cgImage = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
        let durationMs = (CFAbsoluteTimeGetCurrent() - startTime) * 1000.0
        let pHash = computePerceptualHash(cgImage: cgImage)

        return CaptureSnapshot(
            cgImage: cgImage,
            width: display.width,
            height: display.height,
            displayId: Int(display.displayID),
            captureDurationMs: durationMs,
            perceptualHash: pHash
        )
    }

    public func computePerceptualHash(cgImage: CGImage) -> String {
        let hashWidth = 8
        let hashHeight = 8
        let totalPixels = hashWidth * hashHeight

        var rawBytes = [UInt8](repeating: 0, count: totalPixels)
        let colorSpace = CGColorSpaceCreateDeviceGray()
        guard let context = CGContext(
            data: &rawBytes,
            width: hashWidth,
            height: hashHeight,
            bitsPerComponent: 8,
            bytesPerRow: hashWidth,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.none.rawValue
        ) else {
            return "0000000000000000"
        }

        context.interpolationQuality = .low
        context.draw(cgImage, in: CGRect(x: 0, y: 0, width: hashWidth, height: hashHeight))

        var sum: UInt64 = 0
        for byte in rawBytes {
            sum += UInt64(byte)
        }
        let avg = UInt8(sum / UInt64(totalPixels))

        var hashBits: UInt64 = 0
        for i in 0..<totalPixels {
            if rawBytes[i] >= avg {
                hashBits |= (1 << UInt64(i))
            }
        }

        return String(format: "%016llx", hashBits)
    }

    public func hammingDistance(hash1: String, hash2: String) -> Int {
        guard let v1 = UInt64(hash1, radix: 16), let v2 = UInt64(hash2, radix: 16) else {
            return 64
        }
        let xorVal = v1 ^ v2
        return xorVal.nonzeroBitCount
    }
}
