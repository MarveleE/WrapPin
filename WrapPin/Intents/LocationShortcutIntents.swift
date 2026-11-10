import AppIntents

// Both intents run with WrapPin in the foreground: starting may hand off to the
// tunnel app and starts the background keep-alive, and sessions are never
// started from a background task.
struct StartFavouriteSimulationIntent: AppIntent {
    static let title: LocalizedStringResource = "Simulate Favourite Place"
    static let description = IntentDescription("Opens WrapPin and starts simulating a saved favourite place on this iPhone.")
    static let openAppWhenRun = true

    @available(iOS 26, *)
    static let supportedModes: IntentModes = .foreground(.immediate)

    @Parameter(title: "Favourite Place")
    var place: FavouritePlaceEntity

    @Dependency private var appModel: AppModel

    init() {}

    init(place: FavouritePlaceEntity) {
        self.place = place
    }

    static var parameterSummary: some ParameterSummary {
        Summary("Simulate \(\.$place)")
    }

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let target = try await appModel.requestShortcutStart(favouriteID: place.id)
        return .result(dialog: "Starting \(target.name). Check WrapPin for the connection.")
    }
}

struct RestoreRealLocationIntent: AppIntent {
    static let title: LocalizedStringResource = "Stop and Restore Real Location"
    static let description = IntentDescription("Opens WrapPin, stops the running simulation or restores the real location after an interrupted one, and waits for the result.")
    static let openAppWhenRun = true

    @available(iOS 26, *)
    static let supportedModes: IntentModes = .foreground(.immediate)

    @Dependency private var appModel: AppModel

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        switch try await appModel.performShortcutStop() {
        case .stopped, .restored:
            return .result(dialog: IntentDialog(LocalizedStringResource("The real location is restored.")))
        case .nothingToStop:
            return .result(dialog: IntentDialog(LocalizedStringResource("No simulation is running.")))
        }
    }
}

// Composable actions: Shortcuts owns system settings and launching other apps.
struct PrepareFavouriteAutomationIntent: AppIntent {
    static let title: LocalizedStringResource = "Prepare Favourite Automation"
    static let description = IntentDescription("Starts a favourite and waits until cellular data should be turned off or simulation is active. Returns true only when cellular data needs to be turned off.")
    static let openAppWhenRun = true

    @available(iOS 26, *)
    static let supportedModes: IntentModes = .foreground(.immediate)

    @Parameter(title: "Favourite Place")
    var place: FavouritePlaceEntity

    @Dependency private var appModel: AppModel

    static var parameterSummary: some ParameterSummary {
        Summary("Prepare automation for \(\.$place)")
    }

    @MainActor
    func perform() async throws -> some IntentResult & ReturnsValue<Bool> {
        .result(value: try await appModel.prepareShortcutAutomation(favouriteID: place.id))
    }
}

struct WaitForFavouriteAutomationIntent: AppIntent {
    static let title: LocalizedStringResource = "Wait for Favourite Simulation"
    static let description = IntentDescription("Waits up to 25 seconds for the prepared favourite. Returns false on failure or timeout. Restore cellular data immediately after this action, before checking its result.")
    static let openAppWhenRun = true

    @available(iOS 26, *)
    static let supportedModes: IntentModes = .foreground(.immediate)

    @Dependency private var appModel: AppModel

    @MainActor
    func perform() async throws -> some IntentResult & ReturnsValue<Bool> {
        .result(value: await appModel.waitForShortcutAutomation())
    }
}
