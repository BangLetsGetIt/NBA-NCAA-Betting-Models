//
//  CourtSideApp.swift
//  CourtSide Analytics
//
//  Main app entry point
//

import SwiftUI
import Combine

@main
struct CourtSideApp: App {
    @StateObject private var subscriptionManager = SubscriptionManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(subscriptionManager)
                .preferredColorScheme(.dark) // Force dark mode
        }
    }
}

// MARK: - Content View (Tab Navigation)

struct ContentView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @State private var selectedTab = 0
    @State private var showPaywall = false

    var body: some View {
        TabView(selection: $selectedTab) {
            // Today's Picks Tab
            PicksView()
                .tabItem {
                    Label("Projections", systemImage: "basketball.fill")
                }
                .tag(0)

            // Performance Tab
            PerformanceView()
                .tabItem {
                    Label("Performance", systemImage: "chart.line.uptrend.xyaxis")
                }
                .tag(1)

            // Settings Tab
            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
                .tag(2)
        }
        .accentColor(.blue)
        .sheet(isPresented: $showPaywall) {
            PaywallView()
        }
        .onAppear {
            // Show paywall on first launch if not subscribed
            if !subscriptionManager.isSubscribed && !subscriptionManager.hasSeenPaywall {
                DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
                    showPaywall = true
                    subscriptionManager.hasSeenPaywall = true
                }
            }
        }
    }
}

// MARK: - Settings View

struct SettingsView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @State private var showPaywall = false

    var body: some View {
        NavigationView {
            ZStack {
                LinearGradient(
                    colors: [Color(hex: "0f172a"), Color(hex: "1e293b")],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()

                List {
                    // Subscription Section
                    Section {
                        HStack {
                            Image(systemName: subscriptionManager.isSubscribed ? "crown.fill" : "crown")
                                .foregroundColor(subscriptionManager.isSubscribed ? .yellow : .gray)

                            VStack(alignment: .leading, spacing: 4) {
                                Text(subscriptionManager.isSubscribed ? "Pro Member" : "Free User")
                                    .font(.system(size: 16, weight: .semibold, design: .rounded))

                                Text(subscriptionManager.isSubscribed ? "All features unlocked" : "Limited access")
                                    .font(.system(size: 12, weight: .medium, design: .rounded))
                                    .foregroundColor(.secondary)
                            }

                            Spacer()

                            if !subscriptionManager.isSubscribed {
                                Button("Upgrade") {
                                    showPaywall = true
                                }
                                .font(.system(size: 14, weight: .bold, design: .rounded))
                                .padding(.horizontal, 16)
                                .padding(.vertical, 8)
                                .background(Color.blue)
                                .foregroundColor(.white)
                                .cornerRadius(20)
                            }
                        }
                    } header: {
                        Text("Subscription")
                    }
                    .listRowBackground(Color.white.opacity(0.05))

                    // App Info Section
                    Section {
                        HStack {
                            Text("Version")
                            Spacer()
                            Text("1.0.0")
                                .foregroundColor(.secondary)
                        }

                        NavigationLink("Terms of Service") {
                            Text("Terms of Service")
                        }

                        NavigationLink("Privacy Policy") {
                            Text("Privacy Policy")
                        }

                        Button("Contact Support") {
                            // TODO: Open email or support form
                        }
                    } header: {
                        Text("About")
                    }
                    .listRowBackground(Color.white.opacity(0.05))

                    // Account Actions
                    if subscriptionManager.isSubscribed {
                        Section {
                            Button("Manage Subscription") {
                                // TODO: Open App Store subscription management
                                if let url = URL(string: "https://apps.apple.com/account/subscriptions") {
                                    UIApplication.shared.open(url)
                                }
                            }
                        } header: {
                            Text("Account")
                        }
                        .listRowBackground(Color.white.opacity(0.05))
                    }
                }
                .scrollContentBackground(.hidden)
            }
            .navigationTitle("Settings")
            .sheet(isPresented: $showPaywall) {
                PaywallView()
            }
        }
    }
}

// MARK: - Subscription Manager

class SubscriptionManager: ObservableObject {
    @Published var isSubscribed: Bool = false
    @Published var hasSeenPaywall: Bool = false

    init() {
        configureRevenueCat()
        checkSubscriptionStatus()
    }

    private func configureRevenueCat() {
        // TODO: Uncomment after adding RevenueCat package and updating Config.swift
        /*
        Purchases.logLevel = AppConfig.enableDebugLogging ? .debug : .info
        Purchases.configure(withAPIKey: AppConfig.revenueCatAPIKey)

        if AppConfig.enableDebugLogging {
            print("✅ RevenueCat configured with API key")
        }
        */
    }

    func checkSubscriptionStatus() {
        // TODO: Uncomment after adding RevenueCat package
        /*
        Purchases.shared.getCustomerInfo { [weak self] customerInfo, error in
            DispatchQueue.main.async {
                if let error = error {
                    print("❌ Error fetching subscription status: \(error.localizedDescription)")
                    self?.isSubscribed = false
                    return
                }

                // Check if user has active "pro" entitlement
                let hasProAccess = customerInfo?.entitlements[AppConfig.proEntitlementID]?.isActive == true
                self?.isSubscribed = hasProAccess

                if AppConfig.enableDebugLogging {
                    print("✅ Subscription status: \(hasProAccess ? "Active" : "Inactive")")
                }
            }
        }
        */
    }

    func restorePurchases(completion: @escaping (Bool, Error?) -> Void) {
        // TODO: Uncomment after adding RevenueCat package
        /*
        Purchases.shared.restorePurchases { [weak self] customerInfo, error in
            DispatchQueue.main.async {
                if let error = error {
                    completion(false, error)
                    return
                }

                let hasProAccess = customerInfo?.entitlements[AppConfig.proEntitlementID]?.isActive == true
                self?.isSubscribed = hasProAccess
                completion(hasProAccess, nil)
            }
        }
        */
    }
}

// MARK: - Preview

#Preview {
    ContentView()
        .environmentObject(SubscriptionManager())
}
