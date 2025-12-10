//
//  Models.swift
//  CourtSide Analytics
//
//  Data models matching your FastAPI backend
//

import Foundation

// MARK: - API Response Models

struct APIResponse: Codable {
    let metadata: PerformanceStats
    let games: [GamePrediction]
}

struct PerformanceStats: Codable {
    let winRate: Double
    let totalPicks: Int
    let wins: Int
    let losses: Int
    let pushes: Int
    let totalProfit: Double
    let roi: Double
    let spreadRecord: String
    let totalRecord: String
    let lastUpdated: String

    enum CodingKeys: String, CodingKey {
        case winRate = "win_rate"
        case totalPicks = "total_picks"
        case wins, losses, pushes
        case totalProfit = "total_profit"
        case roi
        case spreadRecord = "spread_record"
        case totalRecord = "total_record"
        case lastUpdated = "last_updated"
    }

    // Helper computed properties
    var winRateFormatted: String {
        String(format: "%.1f%%", winRate)
    }

    var profitFormatted: String {
        String(format: "%+.2f", totalProfit)
    }

    var roiFormatted: String {
        String(format: "%+.1f%%", roi)
    }

    var isElitePerformance: Bool {
        winRate >= 60.0
    }

    var isProfitable: Bool {
        totalProfit > 0
    }
}

struct GamePrediction: Codable, Identifiable {
    let homeTeam: String
    let awayTeam: String
    let matchup: String
    let gameDate: String
    let pickType: String
    let pickDescription: String
    let marketLine: Double
    let modelLine: Double?
    let edge: Double
    let odds: Int
    let confidence: String
    let status: String
    let result: String?
    let profitLoss: Double?

    enum CodingKeys: String, CodingKey {
        case homeTeam = "home_team"
        case awayTeam = "away_team"
        case matchup
        case gameDate = "game_date"
        case pickType = "pick_type"
        case pickDescription = "pick_description"
        case marketLine = "market_line"
        case modelLine = "model_line"
        case edge, odds, confidence, status, result
        case profitLoss = "profit_loss"
    }

    // Identifiable conformance
    var id: String {
        "\(homeTeam)_\(awayTeam)_\(gameDate)_\(pickType)"
    }

    // Helper computed properties
    var isPending: Bool {
        status == "pending"
    }

    var isWin: Bool {
        status == "win"
    }

    var isLoss: Bool {
        status == "loss"
    }

    var formattedGameTime: String {
        guard let date = ISO8601DateFormatter().date(from: gameDate) else {
            return gameDate
        }
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d, h:mm a"
        formatter.timeZone = .current
        return formatter.string(from: date)
    }

    var confidenceColor: String {
        switch confidence {
        case "High": return "green"
        case "Medium": return "orange"
        default: return "gray"
        }
    }

    var edgeFormatted: String {
        String(format: "%+.1f pts", edge)
    }

    var oddsFormatted: String {
        odds >= 0 ? "+\(odds)" : "\(odds)"
    }
}

// MARK: - Filter & Sort Options

enum PickFilter: String, CaseIterable {
    case all = "All"
    case spreads = "Spreads"
    case totals = "Totals"

    var apiValue: String? {
        switch self {
        case .all: return nil
        case .spreads: return "Spread"
        case .totals: return "Total"
        }
    }
}

enum ConfidenceFilter: String, CaseIterable {
    case all = "All"
    case high = "High"
    case medium = "Medium"
    case low = "Low"

    var value: String? {
        self == .all ? nil : rawValue
    }
}

enum SortOption: String, CaseIterable {
    case confidence = "Confidence"
    case edge = "Edge"
    case gameTime = "Game Time"
}
