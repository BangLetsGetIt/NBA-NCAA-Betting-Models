//
//  Config.swift
//  CourtSide Analytics
//
//  Configuration file for API keys and sensitive data
//

import Foundation

struct AppConfig {
    // MARK: - RevenueCat Configuration

    /// Your RevenueCat API Key from https://app.revenuecat.com/
    /// Format: appl_xxxxxxxxxxxxxxxxxxxxxxxx (for iOS)
    static let revenueCatAPIKey = "YOUR_REVENUECAT_API_KEY_HERE"

    /// RevenueCat Entitlement Identifier
    /// This should match what you set up in RevenueCat dashboard
    static let proEntitlementID = "pro"

    // MARK: - API Configuration

    /// Backend API URL
    /// - Local testing: "http://localhost:8000"
    /// - Production: "https://your-app.onrender.com"
    static let apiBaseURL = "https://nba-analytics-api-rf2z.onrender.com"

    // MARK: - In-App Purchase Product IDs

    /// These should match your App Store Connect product IDs
    static let monthlyProductID = "pro_monthly"
    static let annualProductID = "pro_annual"

    // MARK: - Feature Flags

    /// Enable debug logging for development
    static let enableDebugLogging = true

    /// Show subscription paywall on first launch
    static let showPaywallOnFirstLaunch = true
}
