//
//  GameCardView.swift
//  CourtSide Analytics
//
//  Glassmorphism card for individual game picks
//

import SwiftUI

struct GameCardView: View {
    let game: GamePrediction
    let isSubscribed: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header: Teams & Time
            VStack(alignment: .leading, spacing: 4) {
                Text(game.matchup)
                    .font(.system(size: 18, weight: .bold, design: .rounded))
                    .foregroundColor(.white)

                HStack {
                    Image(systemName: "clock.fill")
                        .font(.caption)
                    Text(game.formattedGameTime)
                        .font(.system(size: 13, weight: .medium, design: .rounded))
                }
                .foregroundColor(.white.opacity(0.7))
            }

            Divider()
                .background(Color.white.opacity(0.2))

            // Pick Details (Blurred if not subscribed)
            ZStack {
                VStack(alignment: .leading, spacing: 8) {
                    // Pick Type Badge
                    HStack {
                        Text(game.pickType)
                            .font(.system(size: 11, weight: .bold, design: .rounded))
                            .textCase(.uppercase)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(pickTypeColor.opacity(0.2))
                            .foregroundColor(pickTypeColor)
                            .cornerRadius(6)

                        Spacer()

                        // Confidence Badge
                        HStack(spacing: 4) {
                            Circle()
                                .fill(confidenceColor)
                                .frame(width: 8, height: 8)
                            Text(game.confidence)
                                .font(.system(size: 12, weight: .semibold, design: .rounded))
                                .foregroundColor(confidenceColor)
                        }
                    }

                    // The Pick
                    Text(game.pickDescription)
                        .font(.system(size: 22, weight: .heavy, design: .rounded))
                        .foregroundColor(.green)

                    // Stats Grid
                    HStack(spacing: 20) {
                        StatItem(label: "Edge", value: game.edgeFormatted, color: .orange)
                        StatItem(label: "Odds", value: game.oddsFormatted, color: .white.opacity(0.8))
                        if let modelLine = game.modelLine {
                            StatItem(label: "Model", value: String(format: "%.1f", modelLine), color: .cyan)
                        }
                    }
                }
                .blur(radius: isSubscribed ? 0 : 12)

                // Lock Overlay
                if !isSubscribed {
                    VStack(spacing: 8) {
                        Image(systemName: "lock.fill")
                            .font(.system(size: 40))
                            .foregroundColor(.white)

                        Text("Subscribe to Unlock")
                            .font(.system(size: 14, weight: .semibold, design: .rounded))
                            .foregroundColor(.white)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(.ultraThinMaterial)
                    .cornerRadius(12)
                }
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.ultraThinMaterial)
                .shadow(color: .black.opacity(0.3), radius: 10, x: 0, y: 4)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(confidenceColor.opacity(0.3), lineWidth: 2)
        )
    }

    // MARK: - Helpers

    private var pickTypeColor: Color {
        game.pickType == "Spread" ? .blue : .purple
    }

    private var confidenceColor: Color {
        switch game.confidence {
        case "High": return .green
        case "Medium": return .orange
        default: return .gray
        }
    }
}

// MARK: - Stat Item Component

struct StatItem: View {
    let label: String
    let value: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.system(size: 10, weight: .medium, design: .rounded))
                .textCase(.uppercase)
                .foregroundColor(.white.opacity(0.5))

            Text(value)
                .font(.system(size: 16, weight: .bold, design: .rounded))
                .foregroundColor(color)
        }
    }
}

// MARK: - Preview

#Preview {
    ZStack {
        Color.black.ignoresSafeArea()

        VStack(spacing: 20) {
            GameCardView(
                game: GamePrediction(
                    homeTeam: "Los Angeles Lakers",
                    awayTeam: "Boston Celtics",
                    matchup: "Boston Celtics @ Los Angeles Lakers",
                    gameDate: "2025-12-09T19:30:00Z",
                    pickType: "Spread",
                    pickDescription: "Los Angeles Lakers -4.5",
                    marketLine: -4.5,
                    modelLine: -7.2,
                    edge: 2.7,
                    odds: -110,
                    confidence: "High",
                    status: "pending",
                    result: nil,
                    profitLoss: nil
                ),
                isSubscribed: true
            )
            .padding()

            GameCardView(
                game: GamePrediction(
                    homeTeam: "Golden State Warriors",
                    awayTeam: "Phoenix Suns",
                    matchup: "Phoenix Suns @ Golden State Warriors",
                    gameDate: "2025-12-09T22:00:00Z",
                    pickType: "Total",
                    pickDescription: "OVER 225.5",
                    marketLine: 225.5,
                    modelLine: 232.1,
                    edge: 6.6,
                    odds: -110,
                    confidence: "Medium",
                    status: "pending",
                    result: nil,
                    profitLoss: nil
                ),
                isSubscribed: false
            )
            .padding()
        }
    }
}
