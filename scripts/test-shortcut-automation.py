#!/usr/bin/env python3
"""Exercise the production automation methods with a controllable session.

Only the two automation methods are compiled; hardware is replaced by a fake.
Deadlines are shortened to exercise timeout handling without a 25-second wait.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'WrapPin/App/AppModel+Shortcuts.swift').read_text()
methods = source[source.index('    func prepareShortcutAutomation'):source.index('    /// Stops the running simulation')]
methods = methods.replace('.seconds(25)', '.milliseconds(15)').replace('.milliseconds(200)', '.milliseconds(1)')
harness = r'''
import Foundation
struct LocationTarget { let id: String }
enum Phase { case idle, openingLocalDevVPN, discovering, connecting, active(LocationTarget), stopping, failed(String) }
enum Guidance { case connectionHelp, turnOff, turnBackOn }
enum ShortcutFailure: Error { case busy, stopFailed(String), automationTimedOut }
@MainActor final class Session {
    var phase: Phase = .idle
    var mobileDataGuidance: Guidance?
    var confirmed = false
    func useMobileDataGuidance() { mobileDataGuidance = .turnOff }
    func confirmMobileDataIsOff() { confirmed = true }
}
@MainActor final class AppModel {
    let deviceSession = Session()
    var shortcutAutomationTargetID: String?
    var shortcutRequest: Int?
    var hasLiveLocationSession = false
    var isRunningRouteSession = false
    var stopped = false
    var start: () -> Void = {}
    func requestShortcutStart(favouriteID: String) async throws -> LocationTarget {
        shortcutRequest = 1
        return LocationTarget(id: favouriteID)
    }
    func coordinateMode(for target: LocationTarget) -> Int { 0 }
    func startLocationSession(at target: LocationTarget, coordinateMode: Int) async { start() }
    func stopLocationSession() { stopped = true; shortcutAutomationTargetID = nil }
'''
tests = r'''
}
@main struct Tests {
    @MainActor static func main() async throws {
        let direct = AppModel()
        direct.start = { direct.deviceSession.phase = .active(LocationTarget(id: "A")) }
        let needsOff = try await direct.prepareShortcutAutomation(favouriteID: "A")
        assert(!needsOff)
        let ready = await direct.waitForShortcutAutomation()
        assert(ready && direct.shortcutAutomationTargetID == nil)

        let cellular = AppModel()
        cellular.start = {
            cellular.deviceSession.phase = .discovering
            cellular.deviceSession.mobileDataGuidance = .connectionHelp
        }
        let off = try await cellular.prepareShortcutAutomation(favouriteID: "A")
        assert(off)
        cellular.deviceSession.phase = .active(LocationTarget(id: "A"))
        let connected = await cellular.waitForShortcutAutomation()
        assert(connected && cellular.deviceSession.confirmed)

        for phase in [Phase.failed("failed"), .idle, .stopping, .active(LocationTarget(id: "B")), .connecting] {
            let model = AppModel()
            model.shortcutAutomationTargetID = "A"
            model.deviceSession.phase = phase
            let result = await model.waitForShortcutAutomation()
            assert(!result && model.shortcutAutomationTargetID == nil)
        }
        let noRequest = await AppModel().waitForShortcutAutomation()
        assert(!noRequest)

        let timeout = AppModel()
        timeout.start = { timeout.deviceSession.phase = .discovering }
        do {
            _ = try await timeout.prepareShortcutAutomation(favouriteID: "A")
            fatalError("Expected timeout")
        } catch ShortcutFailure.automationTimedOut {}
        assert(timeout.stopped && timeout.shortcutAutomationTargetID == nil)

        let busy = AppModel()
        busy.hasLiveLocationSession = true
        do {
            _ = try await busy.prepareShortcutAutomation(favouriteID: "A")
            fatalError("Expected busy")
        } catch ShortcutFailure.busy {}
        assert(busy.shortcutRequest == nil)

        let cancelled = AppModel()
        cancelled.shortcutAutomationTargetID = "A"
        cancelled.deviceSession.phase = .connecting
        let task = Task { await cancelled.waitForShortcutAutomation() }
        task.cancel()
        let result = await task.value
        assert(!result && cancelled.shortcutAutomationTargetID == nil)
        print("Shortcut automation: direct connection, cellular handoff, failure, timeout, wrong target, busy and cancellation passed")
    }
}
'''
with tempfile.TemporaryDirectory(prefix='wrappin-shortcuts-') as directory:
    swift = Path(directory) / 'Tests.swift'
    binary = Path(directory) / 'tests'
    swift.write_text(harness + methods + tests)
    subprocess.run(['swiftc', '-parse-as-library', str(swift), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
