// EmbeddedHTTPServer — Lightweight HTTP server for Shortcuts / n8n / Node-RED
// Runs on port 3000 by default, exposes FoKS actions as REST endpoints
// Uses NWListener (Network.framework) — zero dependencies

import Foundation
import Network
import os.log

private let logger = Logger(subsystem: "us.giovannini.foks", category: "HTTPServer")

public actor EmbeddedHTTPServer {
    private let port: UInt16
    private var listener: NWListener?

    /// Route table — path → handler. Populated by FoKSHub at startup.
    private var routes: [String: @Sendable (Data?) async -> (Int, [String: Any])] = [:]

    public init(port: UInt16) {
        self.port = port
    }

    // MARK: - Route Registration

    public func registerRoute(_ path: String, handler: @escaping @Sendable (Data?) async -> (Int, [String: Any])) {
        routes[path] = handler
        logger.info("Registered route: \(path)")
    }

    // MARK: - Lifecycle

    public func start() {
        do {
            let params = NWParameters.tcp
            params.allowLocalEndpointReuse = true
            listener = try NWListener(using: params, on: NWEndpoint.Port(rawValue: port)!)
            listener?.stateUpdateHandler = { state in
                switch state {
                case .ready:
                    logger.info("HTTP server listening on :\(self.port)")
                case .failed(let err):
                    logger.error("HTTP server failed: \(err.localizedDescription)")
                default: break
                }
            }
            listener?.newConnectionHandler = { [weak self] conn in
                Task { await self?.handleConnection(conn) }
            }
            listener?.start(queue: .global(qos: .userInitiated))
        } catch {
            logger.error("Failed to start HTTP server: \(error.localizedDescription)")
        }
    }

    public func stop() {
        listener?.cancel()
        listener = nil
        logger.info("HTTP server stopped")
    }

    // MARK: - Connection Handling

    private func handleConnection(_ conn: NWConnection) {
        conn.start(queue: .global(qos: .userInitiated))
        conn.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] data, _, _, error in
            guard let self, let data, error == nil else {
                conn.cancel(); return
            }
            Task { await self.processRequest(data: data, connection: conn) }
        }
    }

    private func processRequest(data: Data, connection: NWConnection) async {
        guard let raw = String(data: data, encoding: .utf8) else {
            await sendResponse(connection: connection, status: 400, body: ["error": "Bad request"])
            return
        }

        // Parse HTTP request line: "POST /path HTTP/1.1\r\n..."
        let lines = raw.components(separatedBy: "\r\n")
        guard let requestLine = lines.first else {
            await sendResponse(connection: connection, status: 400, body: ["error": "No request line"])
            return
        }
        let parts = requestLine.split(separator: " ")
        guard parts.count >= 2 else {
            await sendResponse(connection: connection, status: 400, body: ["error": "Malformed request"])
            return
        }
        let path = String(parts[1])

        // Extract body (after empty line)
        var requestBody: Data?
        if let separatorIdx = raw.range(of: "\r\n\r\n") {
            let bodyString = String(raw[separatorIdx.upperBound...])
            requestBody = bodyString.data(using: .utf8)
        }

        // Route dispatch
        if let handler = routes[path] {
            let (status, body) = await handler(requestBody)
            await sendResponse(connection: connection, status: status, body: body)
        } else {
            await sendResponse(connection: connection, status: 404, body: ["error": "Not found: \(path)"])
        }

        logger.debug("HTTP \(requestLine)")
    }

    private func sendResponse(connection: NWConnection, status: Int, body: [String: Any]) {
        let jsonData = (try? JSONSerialization.data(withJSONObject: body)) ?? Data()
        let statusText = status == 200 ? "OK" : (status == 404 ? "Not Found" : "Error")
        let response = "HTTP/1.1 \(status) \(statusText)\r\nContent-Type: application/json\r\nContent-Length: \(jsonData.count)\r\nConnection: close\r\n\r\n"
        var responseData = response.data(using: .utf8)!
        responseData.append(jsonData)
        connection.send(content: responseData, completion: .contentProcessed { _ in
            connection.cancel()
        })
    }
}
