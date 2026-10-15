import Foundation
import AppKit
import CoreGraphics
import ApplicationServices

public struct WindowInfo: Codable {
    public let id: Int
    public let appName: String
    public let title: String
    public let bundleId: String?
    public let pid: Int
    public let bounds: [String: Double]
    public let layer: Int
    public let isOnScreen: Bool

    public init(id: Int, appName: String, title: String, bundleId: String?, pid: Int, bounds: [String: Double], layer: Int, isOnScreen: Bool) {
        self.id = id
        self.appName = appName
        self.title = title
        self.bundleId = bundleId
        self.pid = pid
        self.bounds = bounds
        self.layer = layer
        self.isOnScreen = isOnScreen
    }
}

public struct AccessibilityNode: Codable {
    public let role: String
    public let title: String?
    public let value: String?
    public let description: String?
    public let document: String?

    public init(role: String, title: String?, value: String?, description: String?, document: String?) {
        self.role = role
        self.title = title
        self.value = value
        self.description = description
        self.document = document
    }
}

public struct AppMetadata: Codable {
    public let appName: String
    public let bundleId: String?
    public let windowTitle: String
    public let pid: Int
    public let accessibilitySummary: String
    public let accessibilityNodes: [AccessibilityNode]

    public init(appName: String, bundleId: String?, windowTitle: String, pid: Int, accessibilitySummary: String = "", accessibilityNodes: [AccessibilityNode] = []) {
        self.appName = appName
        self.bundleId = bundleId
        self.windowTitle = windowTitle
        self.pid = pid
        self.accessibilitySummary = accessibilitySummary
        self.accessibilityNodes = accessibilityNodes
    }
}

public final class WindowInspector {
    public static let shared = WindowInspector()

    private init() {}

    public func getFrontmostApp() -> AppMetadata {
        let frontApp = NSWorkspace.shared.frontmostApplication
        let appName = frontApp?.localizedName ?? "Unknown"
        let bundleId = frontApp?.bundleIdentifier
        let pid = Int(frontApp?.processIdentifier ?? 0)
        var windowTitle = ""

        if let windowList = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] {
            for win in windowList {
                if let ownerPid = win[kCGWindowOwnerPID as String] as? Int, ownerPid == pid {
                    if let title = win[kCGWindowName as String] as? String, !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        windowTitle = title
                        break
                    }
                }
            }
        }

        // Extract UI Accessibility Tree with non-blocking timeout safety
        let axNodes = extractAccessibilityTree(pid: pid_t(pid), maxElements: 20)
        let axSummary = axNodes.compactMap { node -> String? in
            var parts: [String] = []
            if let t = node.title, !t.isEmpty { parts.append(t) }
            if let v = node.value, !v.isEmpty { parts.append(v) }
            if let d = node.description, !d.isEmpty { parts.append(d) }
            if let doc = node.document, !doc.isEmpty { parts.append("[\(doc)]") }
            return parts.isEmpty ? nil : parts.joined(separator: " | ")
        }.joined(separator: "\n")

        return AppMetadata(
            appName: appName,
            bundleId: bundleId,
            windowTitle: windowTitle,
            pid: pid,
            accessibilitySummary: axSummary,
            accessibilityNodes: axNodes
        )
    }

    public func extractAccessibilityTree(pid: pid_t, maxElements: Int = 20) -> [AccessibilityNode] {
        guard pid > 0 else { return [] }
        var nodes: [AccessibilityNode] = []

        let appRef = AXUIElementCreateApplication(pid)
        var focusedElemValue: AnyObject?
        let axRes = AXUIElementCopyAttributeValue(appRef, kAXFocusedUIElementAttribute as CFString, &focusedElemValue)

        if axRes == .success, let focusedElem = focusedElemValue {
            let elemRef = focusedElem as! AXUIElement
            if let node = parseAXElement(elemRef) {
                nodes.append(node)
            }
        }

        // Also inspect main window children
        var mainWindowValue: AnyObject?
        if AXUIElementCopyAttributeValue(appRef, kAXMainWindowAttribute as CFString, &mainWindowValue) == .success,
           let mainWindow = mainWindowValue {
            let winRef = mainWindow as! AXUIElement
            if let winNode = parseAXElement(winRef) {
                nodes.append(winNode)
            }

            var childrenValue: AnyObject?
            if AXUIElementCopyAttributeValue(winRef, kAXChildrenAttribute as CFString, &childrenValue) == .success,
               let children = childrenValue as? [AXUIElement] {
                for child in children.prefix(maxElements) {
                    if let childNode = parseAXElement(child) {
                        nodes.append(childNode)
                    }
                }
            }
        }

        return nodes
    }

    private func parseAXElement(_ elem: AXUIElement) -> AccessibilityNode? {
        var roleValue: AnyObject?
        var titleValue: AnyObject?
        var valValue: AnyObject?
        var descValue: AnyObject?
        var docValue: AnyObject?

        AXUIElementCopyAttributeValue(elem, kAXRoleAttribute as CFString, &roleValue)
        let role = (roleValue as? String) ?? "AXElement"

        AXUIElementCopyAttributeValue(elem, kAXTitleAttribute as CFString, &titleValue)
        let title = titleValue as? String

        AXUIElementCopyAttributeValue(elem, kAXValueAttribute as CFString, &valValue)
        let val = valValue as? String

        AXUIElementCopyAttributeValue(elem, kAXDescriptionAttribute as CFString, &descValue)
        let desc = descValue as? String

        AXUIElementCopyAttributeValue(elem, kAXDocumentAttribute as CFString, &docValue)
        let doc = docValue as? String

        if title == nil && val == nil && desc == nil && doc == nil {
            return nil
        }

        return AccessibilityNode(role: role, title: title, value: val, description: desc, document: doc)
    }

    public func getOnScreenWindows() -> [WindowInfo] {
        var result: [WindowInfo] = []
        guard let windowList = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] else {
            return result
        }

        let runningApps = NSWorkspace.shared.runningApplications
        var bundleMap: [pid_t: String] = [:]
        for app in runningApps {
            if let bid = app.bundleIdentifier {
                bundleMap[app.processIdentifier] = bid
            }
        }

        for win in windowList {
            let winId = win[kCGWindowNumber as String] as? Int ?? 0
            let ownerName = win[kCGWindowOwnerName as String] as? String ?? "Unknown"
            let title = win[kCGWindowName as String] as? String ?? ""
            let pid = win[kCGWindowOwnerPID as String] as? Int ?? 0
            let layer = win[kCGWindowLayer as String] as? Int ?? 0
            let isOnScreen = (win[kCGWindowIsOnscreen as String] as? Bool) ?? true
            
            var boundsDict: [String: Double] = ["x": 0, "y": 0, "w": 0, "h": 0]
            if let bounds = win[kCGWindowBounds as String] as? [String: Any] {
                boundsDict["x"] = bounds["X"] as? Double ?? 0
                boundsDict["y"] = bounds["Y"] as? Double ?? 0
                boundsDict["w"] = bounds["Width"] as? Double ?? 0
                boundsDict["h"] = bounds["Height"] as? Double ?? 0
            }

            let bundleId = bundleMap[pid_t(pid)]

            if (boundsDict["w"] ?? 0) > 10 && (boundsDict["h"] ?? 0) > 10 {
                result.append(WindowInfo(
                    id: winId,
                    appName: ownerName,
                    title: title,
                    bundleId: bundleId,
                    pid: pid,
                    bounds: boundsDict,
                    layer: layer,
                    isOnScreen: isOnScreen
                ))
            }
        }

        return result
    }
}
