//
//  PicksView.swift
//  CourtSide Analytics
//
//  Main view showing today's picks with filters
//

import SwiftUI

struct PicksView: View {
    @StateObject private var dataFetcher = DataFetcher()
    @State private var selectedFilter: PickFilter = .all
    @State private var selectedConfidence: ConfidenceFilter = .all
    @State private var searchText = ""

    // Change this to true when user subscribes
    @State private var isSubscribed = false

    var body: some View {
        NavigationView {
            ZStack {
                // Background gradient
                LinearGradient(
                    colors: [Color(hex: "0f172a"), Color(hex: "1e293b")],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 20) {
                        // Stats Header
                        if let stats = dataFetcher.stats {
                            StatsHeaderView(stats: stats)
                                .padding(.horizontal)
                        }

                        // Filters
                        FilterBarView(
                            selectedFilter: $selectedFilter,
                            selectedConfidence: $selectedConfidence
                        )
                        .padding(.horizontal)

                        // Picks List
                        LazyVStack(spacing: 16) {
                            ForEach(filteredPicks) { pick in
                                GameCardView(game: pick, isSubscribed: isSubscribed)
                                    .padding(.horizontal)
                            }
                        }

                        if filteredPicks.isEmpty && !dataFetcher.isLoading {
                            EmptyStateView()
                                .padding()
                        }
                    }
                    .padding(.vertical)
                }
                .refreshable {
                    await dataFetcher.fetchPendingPicks()
                }

                // Loading Overlay
                if dataFetcher.isLoading {
                    LoadingView()
                }

                // Error Alert
                if let error = dataFetcher.errorMessage {
                    VStack {
                        Spacer()
                        ErrorBanner(message: error)
                            .padding()
                    }
                }
            }
            .navigationTitle("Today's Projections")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        Task {
                            await dataFetcher.fetchPendingPicks()
                        }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                            .foregroundColor(.white)
                    }
                }
            }
        }
        .task {
            await dataFetcher.fetchPendingPicks()
        }
    }

    // MARK: - Filtered Picks

    private var filteredPicks: [GamePrediction] {
        dataFetcher.pendingPicks
            .filter { pick in
                // Filter by pick type
                if let filterType = selectedFilter.apiValue, pick.pickType != filterType {
                    return false
                }

                // Filter by confidence
                if let confidenceLevel = selectedConfidence.value, pick.confidence != confidenceLevel {
                    return false
                }

                // Filter by search
                if !searchText.isEmpty {
                    let searchLower = searchText.lowercased()
                    return pick.matchup.lowercased().contains(searchLower) ||
                           pick.pickDescription.lowercased().contains(searchLower)
                }

                return true
            }
    }
}

// MARK: - Stats Header View

struct StatsHeaderView: View {
    let stats: PerformanceStats

    var body: some View {
        VStack(spacing: 12) {
            // Main Stats
            HStack(spacing: 16) {
                StatPill(
                    label: "Win Rate",
                    value: stats.winRateFormatted,
                    color: stats.winRate >= 60 ? .green : .orange
                )

                StatPill(
                    label: "Profit",
                    value: "\(stats.profitFormatted)u",
                    color: stats.isProfitable ? .green : .red
                )

                StatPill(
                    label: "ROI",
                    value: stats.roiFormatted,
                    color: stats.roi > 0 ? .green : .red
                )
            }

            // Record
            HStack {
                Image(systemName: "chart.line.uptrend.xyaxis")
                    .font(.caption)
                Text("\(stats.wins)-\(stats.losses)-\(stats.pushes) • \(stats.totalPicks) total picks")
                    .font(.system(size: 12, weight: .medium, design: .rounded))
            }
            .foregroundColor(.white.opacity(0.6))
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.ultraThinMaterial)
        )
    }
}

struct StatPill: View {
    let label: String
    let value: String
    let color: Color

    var body: some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.system(size: 20, weight: .black, design: .rounded))
                .foregroundColor(color)

            Text(label)
                .font(.system(size: 10, weight: .medium, design: .rounded))
                .textCase(.uppercase)
                .foregroundColor(.white.opacity(0.6))
        }
        .frame(maxWidth: .infinity)
    }
}

// MARK: - Filter Bar View

struct FilterBarView: View {
    @Binding var selectedFilter: PickFilter
    @Binding var selectedConfidence: ConfidenceFilter

    var body: some View {
        VStack(spacing: 12) {
            // Pick Type Filter
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(PickFilter.allCases, id: \.self) { filter in
                        FilterChip(
                            title: filter.rawValue,
                            isSelected: selectedFilter == filter
                        ) {
                            selectedFilter = filter
                        }
                    }
                }
            }

            // Confidence Filter
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(ConfidenceFilter.allCases, id: \.self) { confidence in
                        FilterChip(
                            title: confidence.rawValue,
                            isSelected: selectedConfidence == confidence
                        ) {
                            selectedConfidence = confidence
                        }
                    }
                }
            }
        }
    }
}

struct FilterChip: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 14, weight: .semibold, design: .rounded))
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(isSelected ? Color.blue : Color.white.opacity(0.1))
                .foregroundColor(.white)
                .cornerRadius(20)
        }
    }
}

// MARK: - Empty State View

struct EmptyStateView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "basketball.fill")
                .font(.system(size: 60))
                .foregroundColor(.white.opacity(0.3))

            Text("No Picks Match Filters")
                .font(.system(size: 18, weight: .semibold, design: .rounded))
                .foregroundColor(.white.opacity(0.7))

            Text("Try adjusting your filters")
                .font(.system(size: 14, weight: .medium, design: .rounded))
                .foregroundColor(.white.opacity(0.5))
        }
        .padding(40)
    }
}

// MARK: - Loading View

struct LoadingView: View {
    var body: some View {
        ZStack {
            Color.black.opacity(0.4)
                .ignoresSafeArea()

            VStack(spacing: 16) {
                ProgressView()
                    .scaleEffect(1.5)
                    .tint(.white)

                Text("Loading Projections...")
                    .font(.system(size: 16, weight: .medium, design: .rounded))
                    .foregroundColor(.white)
            }
            .padding(32)
            .background(.ultraThinMaterial)
            .cornerRadius(16)
        }
    }
}

// MARK: - Error Banner

struct ErrorBanner: View {
    let message: String

    var body: some View {
        HStack {
            Image(systemName: "exclamationmark.triangle.fill")
            Text(message)
                .font(.system(size: 14, weight: .medium, design: .rounded))
        }
        .foregroundColor(.white)
        .padding()
        .background(Color.red.opacity(0.8))
        .cornerRadius(12)
    }
}

// MARK: - Color Extension

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }

        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

// MARK: - Preview

#Preview {
    PicksView()
}
