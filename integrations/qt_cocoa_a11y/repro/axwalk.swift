import ApplicationServices
import Foundation
let pid = pid_t(CommandLine.arguments[1])!
let seconds = Double(CommandLine.arguments[2])!
print("trusted:", AXIsProcessTrusted())
let app = AXUIElementCreateApplication(pid); AXUIElementSetMessagingTimeout(app, 1.0)
var visited = 0
func walk(_ e: AXUIElement, _ depth: Int) {
    if depth > 60 { return }
    visited += 1
    var names: CFArray?
    if AXUIElementCopyAttributeNames(e, &names) == .success, let ns = names as? [String] {
        var vals: CFArray?
        _ = AXUIElementCopyMultipleAttributeValues(e, ns as CFArray, AXCopyMultipleAttributeOptions(rawValue: 0), &vals)
    }
    var kids: CFTypeRef?
    if AXUIElementCopyAttributeValue(e, kAXChildrenAttribute as CFString, &kids) == .success, let ks = kids as? [AXUIElement] {
        for k in ks { walk(k, depth + 1) }
    }
}
let end = Date().addingTimeInterval(seconds)
var passes = 0
while Date() < end {
    walk(app, 0); passes += 1; usleep(75000)
    if kill(pid, 0) != 0 { print("TARGET DIED after passes:", passes); exit(2) }
}
print("passes:", passes, "elements visited:", visited)
