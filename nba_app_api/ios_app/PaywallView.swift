//
//  PaywallView.swift
//  CourtSide Analytics
//
//  Subscription paywall with RevenueCat integration
//

import SwiftUI

struct PaywallView: View {
    @Environment(\.dismiss) var dismiss
    @State private var selectedPlan: SubscriptionPlan = .monthly
    @State private var isPurchasing = false

    var body: some View {
        ZStack {
            // Background
            LinearGradient(
                colors: [Color(hex: "0f172a"), Color(hex: "1e293b"), Color(hex: "0f172a")],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            ScrollView {
                VStack(spacing: 24) {
                    // Close Button
                    HStack {
                        Spacer()
                        Button {
                            dismiss()
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .font(.title)
                                .foregroundColor(.white.opacity(0.6))
                        }
                    }
                    .padding()

                    // Hero Section
                    VStack(spacing: 16) {
                        Image(systemName: "crown.fill")
                            .font(.system(size: 60))
                            .foregroundColor(.yellow)

                        Text("Unlock Elite Projections")
                            .font(.system(size: 32, weight: .black, design: .rounded))
                            .foregroundColor(.white)
                            .multilineTextAlignment(.center)

                        Text("Join winning bettors using data-driven analytics")
                            .font(.system(size: 16, weight: .medium, design: .rounded))
                            .foregroundColor(.white.opacity(0.7))
                            .multilineTextAlignment(.center)
                    }
                    .padding(.horizontal)

                    // Features Grid
                    VStack(spacing: 16) {
                        FeatureRow(
                            icon: "chart.line.uptrend.xyaxis.circle.fill",
                            title: "60%+ Win Rate",
                            description: "Proven track record with 158+ documented picks",
                            color: .green
                        )

                        FeatureRow(
                            icon: "eye.circle.fill",
                            title: "Full Transparency",
                            description: "Every pick tracked. Every result published.",
                            color: .blue
                        )

                        FeatureRow(
                            icon: "clock.arrow.circlepath",
                            title: "Daily Updates",
                            description: "Fresh projections every morning at 10 AM ET",
                            color: .orange
                        )

                        FeatureRow(
                            icon: "brain.head.profile",
                            title: "AI-Powered Model",
                            description: "Advanced analytics using team stats, rest days, and splits",
                            color: .purple
                        )

                        FeatureRow(
                            icon: "dollarsign.circle.fill",
                            title: "+25.96 Units Profit",
                            description: "Real money. Real results. Real transparency.",
                            color: .green
                        )
                    }
                    .padding(.horizontal)

                    // Subscription Plans
                    VStack(spacing: 12) {
                        Text("Choose Your Plan")
                            .font(.system(size: 20, weight: .bold, design: .rounded))
                            .foregroundColor(.white)

                        SubscriptionPlanCard(
                            plan: .monthly,
                            isSelected: selectedPlan == .monthly
                        ) {
                            selectedPlan = .monthly
                        }

                        SubscriptionPlanCard(
                            plan: .annual,
                            isSelected: selectedPlan == .annual
                        ) {
                            selectedPlan = .annual
                        }
                    }
                    .padding(.horizontal)

                    // Subscribe Button
                    Button {
                        purchase()
                    } label: {
                        HStack {
                            if isPurchasing {
                                ProgressView()
                                    .tint(.white)
                            } else {
                                Text("Start \(selectedPlan.displayName)")
                                    .font(.system(size: 18, weight: .bold, design: .rounded))
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(
                            LinearGradient(
                                colors: [.green, .blue],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .foregroundColor(.white)
                        .cornerRadius(16)
                    }
                    .disabled(isPurchasing)
                    .padding(.horizontal)

                    // Footer
                    VStack(spacing: 8) {
                        Text("Cancel anytime. No hidden fees.")
                            .font(.system(size: 12, weight: .medium, design: .rounded))
                            .foregroundColor(.white.opacity(0.5))

                        HStack(spacing: 16) {
                            Button("Terms") { }
                                .font(.system(size: 11, weight: .medium, design: .rounded))
                                .foregroundColor(.white.opacity(0.5))

                            Button("Privacy") { }
                                .font(.system(size: 11, weight: .medium, design: .rounded))
                                .foregroundColor(.white.opacity(0.5))

                            Button("Restore") {
                                restorePurchases()
                            }
                            .font(.system(size: 11, weight: .medium, design: .rounded))
                            .foregroundColor(.white.opacity(0.5))
                        }
                    }
                    .padding(.bottom, 32)
                }
            }
        }
    }

    // MARK: - Actions

    private func purchase() {
        isPurchasing = true

        // TODO: Uncomment after adding RevenueCat package
        /*
        // Fetch available offerings from RevenueCat
        Purchases.shared.getOfferings { [weak self] offerings, error in
            guard let self = self else { return }

            if let error = error {
                DispatchQueue.main.async {
                    self.isPurchasing = false
                    print("❌ Error fetching offerings: \(error.localizedDescription)")
                    // TODO: Show error alert to user
                }
                return
            }

            // Get the package based on selected plan
            guard let offering = offerings?.current,
                  let package = offering.package(identifier: self.selectedPlan.packageIdentifier) else {
                DispatchQueue.main.async {
                    self.isPurchasing = false
                    print("❌ No package found for: \(self.selectedPlan.packageIdentifier)")
                    // TODO: Show error alert to user
                }
                return
            }

            // Purchase the package
            Purchases.shared.purchase(package: package) { transaction, customerInfo, error, userCancelled in
                DispatchQueue.main.async {
                    self.isPurchasing = false

                    if let error = error {
                        print("❌ Purchase error: \(error.localizedDescription)")
                        // TODO: Show error alert to user
                        return
                    }

                    if userCancelled {
                        print("ℹ️ User cancelled purchase")
                        return
                    }

                    // Check if purchase was successful
                    if customerInfo?.entitlements[AppConfig.proEntitlementID]?.isActive == true {
                        print("✅ Purchase successful!")
                        self.dismiss()
                    }
                }
            }
        }
        */

        // TEMPORARY: Simulate purchase for testing without RevenueCat
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            isPurchasing = false
            print("⚠️ Simulated purchase (RevenueCat not configured)")
            dismiss()
        }
    }

    private func restorePurchases() {
        // TODO: Uncomment after adding RevenueCat package
        /*
        Purchases.shared.restorePurchases { customerInfo, error in
            DispatchQueue.main.async {
                if let error = error {
                    print("❌ Restore error: \(error.localizedDescription)")
                    // TODO: Show error alert
                    return
                }

                if customerInfo?.entitlements[AppConfig.proEntitlementID]?.isActive == true {
                    print("✅ Purchases restored successfully!")
                    // TODO: Show success alert
                    self.dismiss()
                } else {
                    print("ℹ️ No purchases to restore")
                    // TODO: Show info alert
                }
            }
        }
        */

        // TEMPORARY: For testing without RevenueCat
        print("⚠️ Restore purchases (RevenueCat not configured)")
    }
}

// MARK: - Feature Row

struct FeatureRow: View {
    let icon: String
    let title: String
    let description: String
    let color: Color

    var body: some View {
        HStack(spacing: 16) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(color)
                .frame(width: 40)

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.system(size: 16, weight: .bold, design: .rounded))
                    .foregroundColor(.white)

                Text(description)
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundColor(.white.opacity(0.6))
            }

            Spacer()
        }
        .padding()
        .background(Color.white.opacity(0.05))
        .cornerRadius(12)
    }
}

// MARK: - Subscription Plan Card

struct SubscriptionPlanCard: View {
    let plan: SubscriptionPlan
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(plan.displayName)
                            .font(.system(size: 18, weight: .bold, design: .rounded))
                            .foregroundColor(.white)

                        if plan.savingsText != nil {
                            Text(plan.savingsText!)
                                .font(.system(size: 11, weight: .bold, design: .rounded))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(Color.green.opacity(0.2))
                                .foregroundColor(.green)
                                .cornerRadius(8)
                        }
                    }

                    Text(plan.priceText)
                        .font(.system(size: 14, weight: .medium, design: .rounded))
                        .foregroundColor(.white.opacity(0.6))
                }

                Spacer()

                ZStack {
                    Circle()
                        .stroke(isSelected ? Color.blue : Color.white.opacity(0.3), lineWidth: 2)
                        .frame(width: 24, height: 24)

                    if isSelected {
                        Circle()
                            .fill(Color.blue)
                            .frame(width: 16, height: 16)
                    }
                }
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isSelected ? Color.blue.opacity(0.2) : Color.white.opacity(0.05))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(isSelected ? Color.blue : Color.clear, lineWidth: 2)
                    )
            )
        }
    }
}

// MARK: - Subscription Plan Model

enum SubscriptionPlan {
    case monthly
    case annual

    var displayName: String {
        switch self {
        case .monthly: return "Monthly"
        case .annual: return "Annual"
        }
    }

    var priceText: String {
        switch self {
        case .monthly: return "$9.99/month"
        case .annual: return "$79.99/year ($6.67/month)"
        }
    }

    var savingsText: String? {
        switch self {
        case .monthly: return nil
        case .annual: return "Save 33%"
        }
    }

    // TODO: Map to actual RevenueCat package identifiers
    var packageIdentifier: String {
        switch self {
        case .monthly: return "pro_monthly"
        case .annual: return "pro_annual"
        }
    }
}

// MARK: - Preview

#Preview {
    PaywallView()
}
