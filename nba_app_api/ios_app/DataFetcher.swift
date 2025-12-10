//
//  DataFetcher.swift
//  CourtSide Analytics
//
//  Network layer for fetching picks from your FastAPI backend
//

import Foundation
import Combine

@MainActor
class DataFetcher: ObservableObject {

    // MARK: - Published Properties

    @Published var pendingPicks: [GamePrediction] = []
    @Published var completedPicks: [GamePrediction] = []
    @Published var stats: PerformanceStats?
    @Published var isLoading = false
    @Published var errorMessage: String?

    // MARK: - Configuration

    // CHANGE THIS to your deployed API URL when ready
    // For local testing: http://localhost:8000
    // For production: https://your-api.onrender.com
    private let baseURL = "http://localhost:8000"

    // MARK: - Public Methods

    func fetchPendingPicks() async {
        await fetchData(endpoint: "/picks/pending") { [weak self] (response: APIResponse) in
            self?.pendingPicks = response.games
            self?.stats = response.metadata
        }
    }

    func fetchCompletedPicks() async {
        await fetchData(endpoint: "/picks/completed") { [weak self] (response: APIResponse) in
            self?.completedPicks = response.games
        }
    }

    func fetchStats() async {
        await fetchData(endpoint: "/stats") { [weak self] (stats: PerformanceStats) in
            self?.stats = stats
        }
    }

    // MARK: - Private Helpers

    private func fetchData<T: Decodable>(
        endpoint: String,
        completion: @escaping (T) -> Void
    ) async {
        isLoading = true
        errorMessage = nil

        guard let url = URL(string: baseURL + endpoint) else {
            errorMessage = "Invalid URL"
            isLoading = false
            return
        }

        do {
            let (data, response) = try await URLSession.shared.data(from: url)

            // Check for HTTP errors
            guard let httpResponse = response as? HTTPURLResponse else {
                errorMessage = "Invalid response"
                isLoading = false
                return
            }

            guard (200...299).contains(httpResponse.statusCode) else {
                errorMessage = "Server error: \(httpResponse.statusCode)"
                isLoading = false
                return
            }

            // Decode JSON
            let decoder = JSONDecoder()
            let decodedData = try decoder.decode(T.self, from: data)

            completion(decodedData)

        } catch let decodingError as DecodingError {
            errorMessage = "Data format error: \(decodingError.localizedDescription)"
            print("Decoding error: \(decodingError)")
        } catch {
            errorMessage = "Network error: \(error.localizedDescription)"
            print("Network error: \(error)")
        }

        isLoading = false
    }
}

// MARK: - Error Handling

enum DataFetcherError: LocalizedError {
    case invalidURL
    case networkError(Error)
    case decodingError(Error)
    case serverError(Int)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid API URL"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .decodingError(let error):
            return "Data parsing error: \(error.localizedDescription)"
        case .serverError(let code):
            return "Server error: \(code)"
        }
    }
}
