//
//  PerformanceView.swift
//  CourtSide Analytics
//
//  Transparency tab showing model performance with Swift Charts
//

import SwiftUI
import Charts

struct PerformanceView: View {
    @StateObject private var dataFetcher = DataFetcher()

    var body: some View {
        NavigationView {
            ZStack {
                // Background
                LinearGradient(
                    colors: [Color(hex: "0f172a"), Color(hex: "1e293b")],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 24) {
                        // Overall Stats Card
                        if let stats = dataFetcher.stats {
                            OverallStatsCard(stats: stats)
                                .padding(.horizontal)
                        }

                        // Cumulative Profit Chart
                        if !dataFetcher.completedPicks.isEmpty {
                            CumulativeProfitChart(picks: dataFetcher.completedPicks)
                                .padding(.horizontal)
                        }

                        // Win Rate Chart
                        if let stats = dataFetcher.stats {
                            WinRateBreakdownChart(stats: stats)
                                .padding(.horizontal)
                        }

                        // Recent Picks List
                        RecentPicksList(picks: Array(dataFetcher.completedPicks.prefix(10)))
                            .padding(.horizontal)
                    }
                    .padding(.vertical)
                }
                .refreshable {
                    async {
                        await dataFetcher.fetchCompletedPicks()
                        await dataFetcher.fetchStats()
                    }
                }

                if dataFetcher.isLoading {
                    LoadingView()
                }
            }
            .navigationTitle("Model Performance")
            .navigationBarTitleDisplayMode(.large)
        }
        .task {
            await dataFetcher.fetchCompletedPicks()
            await dataFetcher.fetchStats()
        }
    }
}

// MARK: - Overall Stats Card

struct OverallStatsCard: View {
    let stats: PerformanceStats

    var body: some View {
        VStack(spacing: 16) {
            // Title
            HStack {
                Image(systemName: "chart.line.uptrend.xyaxis.circle.fill")
                    .font(.title2)
                    .foregroundColor(.green)

                Text("Overall Performance")
                    .font(.system(size: 20, weight: .bold, design: .rounded))
                    .foregroundColor(.white)

                Spacer()
            }

            // Key Metrics Grid
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 16) {
                MetricCard(
                    title: "Win Rate",
                    value: stats.winRateFormatted,
                    subtitle: "\(stats.wins)-\(stats.losses)-\(stats.pushes)",
                    color: stats.winRate >= 60 ? .green : stats.winRate >= 52.4 ? .orange : .red,
                    icon: "percent"
                )

                MetricCard(
                    title: "Total Profit",
                    value: "\(stats.profitFormatted)u",
                    subtitle: "ROI: \(stats.roiFormatted)",
                    color: stats.isProfitable ? .green : .red,
                    icon: "dollarsign.circle.fill"
                )

                MetricCard(
                    title: "Spreads",
                    value: stats.spreadRecord,
                    subtitle: "Against the spread",
                    color: .blue,
                    icon: "chart.bar.fill"
                )

                MetricCard(
                    title: "Totals",
                    value: stats.totalRecord,
                    subtitle: "Over/Under",
                    color: .purple,
                    icon: "arrow.up.arrow.down"
                )
            }

            // Benchmark Note
            HStack {
                Image(systemName: "info.circle.fill")
                    .foregroundColor(.cyan)
                Text("Industry benchmark: 52.4% to break even • 60%+ is elite")
                    .font(.system(size: 11, weight: .medium, design: .rounded))
                    .foregroundColor(.white.opacity(0.6))
            }
            .padding(.top, 8)
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.ultraThinMaterial)
        )
    }
}

struct MetricCard: View {
    let title: String
    let value: String
    let subtitle: String
    let color: Color
    let icon: String

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundColor(color)

            Text(value)
                .font(.system(size: 22, weight: .black, design: .rounded))
                .foregroundColor(color)

            Text(title)
                .font(.system(size: 12, weight: .semibold, design: .rounded))
                .textCase(.uppercase)
                .foregroundColor(.white.opacity(0.7))

            Text(subtitle)
                .font(.system(size: 10, weight: .medium, design: .rounded))
                .foregroundColor(.white.opacity(0.5))
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color.white.opacity(0.05))
        .cornerRadius(12)
    }
}

// MARK: - Cumulative Profit Chart

struct CumulativeProfitChart: View {
    let picks: [GamePrediction]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "chart.line.uptrend.xyaxis")
                    .foregroundColor(.green)
                Text("Cumulative Profit")
                    .font(.system(size: 18, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
            }

            Chart {
                ForEach(Array(cumulativeData.enumerated()), id: \.offset) { index, data in
                    LineMark(
                        x: .value("Pick", index),
                        y: .value("Profit", data.profit)
                    )
                    .foregroundStyle(
                        LinearGradient(
                            colors: [.green, .cyan],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .lineStyle(StrokeStyle(lineWidth: 3))

                    AreaMark(
                        x: .value("Pick", index),
                        y: .value("Profit", data.profit)
                    )
                    .foregroundStyle(
                        LinearGradient(
                            colors: [.green.opacity(0.3), .cyan.opacity(0.1)],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                }
            }
            .frame(height: 200)
            .chartXAxis {
                AxisMarks(values: .automatic(desiredCount: 5)) { _ in
                    AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5))
                        .foregroundStyle(.white.opacity(0.2))
                    AxisTick(stroke: StrokeStyle(lineWidth: 0.5))
                        .foregroundStyle(.white.opacity(0.5))
                    AxisValueLabel()
                        .foregroundStyle(.white.opacity(0.6))
                }
            }
            .chartYAxis {
                AxisMarks { _ in
                    AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5))
                        .foregroundStyle(.white.opacity(0.2))
                    AxisValueLabel()
                        .foregroundStyle(.white.opacity(0.6))
                }
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.ultraThinMaterial)
        )
    }

    private var cumulativeData: [(pick: Int, profit: Double)] {
        var cumulative: Double = 0
        return picks.enumerated().map { index, pick in
            cumulative += pick.profitLoss ?? 0
            return (index, cumulative)
        }
    }
}

// MARK: - Win Rate Breakdown Chart

struct WinRateBreakdownChart: View {
    let stats: PerformanceStats

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "chart.pie.fill")
                    .foregroundColor(.blue)
                Text("Win Rate Breakdown")
                    .font(.system(size: 18, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
            }

            HStack(spacing: 20) {
                // Spreads
                VStack {
                    Text("Spreads")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .foregroundColor(.white.opacity(0.6))

                    Text(stats.spreadRecord)
                        .font(.system(size: 20, weight: .black, design: .rounded))
                        .foregroundColor(.blue)

                    WinRateBar(record: stats.spreadRecord, color: .blue)
                }
                .frame(maxWidth: .infinity)

                // Totals
                VStack {
                    Text("Totals")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .foregroundColor(.white.opacity(0.6))

                    Text(stats.totalRecord)
                        .font(.system(size: 20, weight: .black, design: .rounded))
                        .foregroundColor(.purple)

                    WinRateBar(record: stats.totalRecord, color: .purple)
                }
                .frame(maxWidth: .infinity)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.ultraThinMaterial)
        )
    }
}

struct WinRateBar: View {
    let record: String
    let color: Color

    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                // Background
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color.white.opacity(0.1))
                    .frame(height: 8)

                // Fill
                RoundedRectangle(cornerRadius: 4)
                    .fill(color)
                    .frame(width: geometry.size.width * winRatePercentage, height: 8)
            }
        }
        .frame(height: 8)
    }

    private var winRatePercentage: CGFloat {
        let components = record.split(separator: "-").compactMap { Int($0) }
        guard components.count >= 2 else { return 0 }
        let wins = components[0]
        let losses = components[1]
        let total = wins + losses
        return total > 0 ? CGFloat(wins) / CGFloat(total) : 0
    }
}

// MARK: - Recent Picks List

struct RecentPicksList: View {
    let picks: [GamePrediction]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "clock.arrow.circlepath")
                    .foregroundColor(.orange)
                Text("Recent Results")
                    .font(.system(size: 18, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
            }

            ForEach(picks) { pick in
                RecentPickRow(pick: pick)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.ultraThinMaterial)
        )
    }
}

struct RecentPickRow: View {
    let pick: GamePrediction

    var body: some View {
        HStack {
            // Result Badge
            Image(systemName: pick.isWin ? "checkmark.circle.fill" : "xmark.circle.fill")
                .foregroundColor(pick.isWin ? .green : .red)
                .font(.title3)

            VStack(alignment: .leading, spacing: 2) {
                Text(pick.matchup)
                    .font(.system(size: 14, weight: .semibold, design: .rounded))
                    .foregroundColor(.white)

                Text(pick.pickDescription)
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundColor(.white.opacity(0.6))
            }

            Spacer()

            if let profit = pick.profitLoss {
                Text(String(format: "%+.2fu", profit))
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                    .foregroundColor(profit >= 0 ? .green : .red)
            }
        }
        .padding()
        .background(Color.white.opacity(0.05))
        .cornerRadius(12)
    }
}

// MARK: - Preview

#Preview {
    PerformanceView()
}
