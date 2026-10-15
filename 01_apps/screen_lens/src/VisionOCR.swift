import Foundation
import Vision
import CoreGraphics

public enum OCRMode: String, Codable {
    case fast = "fast"
    case accurate = "accurate"
}

public struct OCRTextBlock: Codable {
    public let text: String
    public let confidence: Double
    public let bboxX: Double
    public let bboxY: Double
    public let bboxW: Double
    public let bboxH: Double
    public let pixelX: Int
    public let pixelY: Int
    public let pixelW: Int
    public let pixelH: Int

    public init(text: String, confidence: Double, bboxX: Double, bboxY: Double, bboxW: Double, bboxH: Double, pixelX: Int, pixelY: Int, pixelW: Int, pixelH: Int) {
        self.text = text
        self.confidence = confidence
        self.bboxX = bboxX
        self.bboxY = bboxY
        self.bboxW = bboxW
        self.bboxH = bboxH
        self.pixelX = pixelX
        self.pixelY = pixelY
        self.pixelW = pixelW
        self.pixelH = pixelH
    }
}

public struct OCRResult: Codable {
    public let fullText: String
    public let confidenceAvg: Double
    public let textBlocks: [OCRTextBlock]
    public let durationMs: Double
    public let mode: String

    public init(fullText: String, confidenceAvg: Double, textBlocks: [OCRTextBlock], durationMs: Double, mode: String) {
        self.fullText = fullText
        self.confidenceAvg = confidenceAvg
        self.textBlocks = textBlocks
        self.durationMs = durationMs
        self.mode = mode
    }
}

public final class VisionOCR {
    public static let shared = VisionOCR()

    private init() {}

    public func recognizeText(from cgImage: CGImage, mode: OCRMode = .fast, screenWidth: Int? = nil, screenHeight: Int? = nil) -> OCRResult {
        let startTime = CFAbsoluteTimeGetCurrent()
        let width = screenWidth ?? cgImage.width
        let height = screenHeight ?? cgImage.height

        var textBlocks: [OCRTextBlock] = []
        var totalConfidence: Double = 0.0

        let request = VNRecognizeTextRequest { request, error in
            guard error == nil, let observations = request.results as? [VNRecognizedTextObservation] else {
                return
            }

            for observation in observations {
                guard let candidate = observation.topCandidates(1).first else { continue }
                let text = candidate.string.trimmingCharacters(in: .whitespacesAndNewlines)
                if text.isEmpty { continue }

                let confidence = Double(candidate.confidence)
                totalConfidence += confidence

                let bbox = observation.boundingBox
                let bx = Double(bbox.origin.x)
                let by = Double(bbox.origin.y)
                let bw = Double(bbox.size.width)
                let bh = Double(bbox.size.height)

                // Convert normalized Vision coordinates (lower-left origin) to screen pixel coordinates (top-left origin)
                let px = Int(bx * Double(width))
                let py = Int(max(0.0, (1.0 - by - bh)) * Double(height))
                let pw = Int(bw * Double(width))
                let ph = Int(bh * Double(height))

                let block = OCRTextBlock(
                    text: text,
                    confidence: confidence,
                    bboxX: bx,
                    bboxY: by,
                    bboxW: bw,
                    bboxH: bh,
                    pixelX: px,
                    pixelY: py,
                    pixelW: pw,
                    pixelH: ph
                )
                textBlocks.append(block)
            }
        }

        request.recognitionLevel = (mode == .fast) ? .fast : .accurate
        request.usesLanguageCorrection = true
        request.recognitionLanguages = ["en-US"]

        let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
        do {
            try handler.perform([request])
        } catch {
            // If OCR fails, return empty result
        }

        let durationMs = (CFAbsoluteTimeGetCurrent() - startTime) * 1000.0
        let fullText = textBlocks.map { $0.text }.joined(separator: "\n")
        let avgConf = textBlocks.isEmpty ? 0.0 : (totalConfidence / Double(textBlocks.count))

        return OCRResult(
            fullText: fullText,
            confidenceAvg: avgConf,
            textBlocks: textBlocks,
            durationMs: durationMs,
            mode: mode.rawValue
        )
    }
}
