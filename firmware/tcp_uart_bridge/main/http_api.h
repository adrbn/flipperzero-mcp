#pragma once

#include "esp_err.h"
#include "esp_http_server.h"

/**
 * HTTP API for Flipper CLI Bridge
 *
 * REST API that translates HTTP requests to Flipper CLI commands over UART.
 *
 * Endpoints:
 *   GET  /api/health              - Bridge health check
 *   GET  /api/device/info         - Get device info (device_info CLI)
 *   GET  /api/storage/list        - List directory (?path=/ext/badusb)
 *   GET  /api/storage/read        - Read file (?path=/ext/file.txt)
 *   POST /api/storage/write       - Write file {path, content}
 *   POST /api/storage/delete      - Delete file {path}
 *   POST /api/storage/mkdir       - Create directory {path}
 *   POST /api/app/start           - Start app {name, args}
 *   POST /api/cli/command         - Send raw CLI command {command}
 */

/**
 * Initialize and start the HTTP API server.
 *
 * @param port Port to listen on (e.g., 80)
 * @return ESP_OK on success
 */
esp_err_t http_api_init(uint16_t port);

/**
 * Stop the HTTP API server.
 */
void http_api_stop(void);

/**
 * Check if HTTP API server is running.
 *
 * @return true if running
 */
bool http_api_is_running(void);

/**
 * Feed UART data to HTTP API for CLI response processing.
 * Call this from UART RX callback.
 *
 * @param data Received bytes
 * @param len Number of bytes
 */
void http_api_uart_rx(const uint8_t *data, size_t len);
