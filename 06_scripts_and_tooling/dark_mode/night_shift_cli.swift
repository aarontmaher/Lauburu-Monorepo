import Foundation
import CoreGraphics

// Pure Hardware Luminance & Screen Dimmer (Zero-Chroma Monochromatic Control)
func applyHardwareLuminance(brightness: Double) {
    let tableSize: Int = 256
    let maxDisplays: UInt32 = 16
    var activeDisplays = [CGDirectDisplayID](repeating: 0, count: Int(maxDisplays))
    var displayCount: UInt32 = 0
    
    CGGetActiveDisplayList(maxDisplays, &activeDisplays, &displayCount)
    
    var redTable = [CGGammaValue](repeating: 0, count: tableSize)
    var greenTable = [CGGammaValue](repeating: 0, count: tableSize)
    var blueTable = [CGGammaValue](repeating: 0, count: tableSize)
    
    let clampedBrightness = max(0.05, min(1.0, brightness))
    
    for i in 0..<tableSize {
        let val = Float(i) / Float(tableSize - 1)
        let scaled = CGGammaValue(Double(val) * clampedBrightness)
        redTable[i] = scaled
        greenTable[i] = scaled
        blueTable[i] = scaled
    }
    
    for d in 0..<Int(displayCount) {
        let displayID = activeDisplays[d]
        let _ = CGSetDisplayTransferByTable(displayID, UInt32(tableSize), &redTable, &greenTable, &blueTable)
    }
    
    print("✅ System-Wide Screen Luminance Set: \(Int(clampedBrightness * 100))% on \(displayCount) displays")
}

func restoreDefaultDisplay() {
    CGDisplayRestoreColorSyncSettings()
    print("✅ System-Wide Display Settings Restored (100% Brightness)")
}

let args = CommandLine.arguments

if args.contains("--reset") || args.contains("--off") || args.contains("--daylight") {
    restoreDefaultDisplay()
    exit(0)
}

var targetBrightness: Double = 1.0

for i in 0..<args.count {
    if (args[i] == "--brightness" || args[i] == "--dim") && i + 1 < args.count {
        if let b = Double(args[i + 1]) {
            targetBrightness = max(0.05, min(1.0, b))
        }
    }
}

if targetBrightness >= 0.99 {
    restoreDefaultDisplay()
} else {
    applyHardwareLuminance(brightness: targetBrightness)
}
