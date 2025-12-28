/**
 * TCP-UART Bridge for Flipper Zero WiFi Dev Board
 *
 * Main application that bridges TCP socket connections to UART
 * for Flipper Zero Protobuf RPC communication over WiFi.
 *
 * Flow:
 *   MCP Client <--TCP--> ESP32 <--UART--> Flipper Zero
 *
 * Features:
 *   - Web-based captive portal for WiFi configuration
 *   - Stores credentials in NVS (survives reboots)
 *   - Bidirectional TCP<->UART forwarding
 *   - LED status indication
 */

#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_system.h"
#include "driver/gpio.h"

#include "wifi_manager.h"
#include "tcp_server.h"
#include "uart_bridge.h"

static const char *TAG = "main";

/* LED pin for status indication (ESP32-S2 built-in LED varies by board) */
#define STATUS_LED_PIN GPIO_NUM_15

/* Statistics */
static uint32_t s_tcp_to_uart_bytes = 0;
static uint32_t s_uart_to_tcp_bytes = 0;

/**
 * Callback: data received from TCP client -> forward to UART
 */
static void on_tcp_rx(const uint8_t *data, size_t len) {
    int sent = uart_bridge_send(data, len);
    if (sent > 0) {
        s_tcp_to_uart_bytes += sent;
        ESP_LOGD(TAG, "TCP->UART: %zu bytes", len);
    }
}

/**
 * Callback: data received from UART -> forward to TCP client
 */
static void on_uart_rx(const uint8_t *data, size_t len) {
    int sent = tcp_server_send(data, len);
    if (sent > 0) {
        s_uart_to_tcp_bytes += sent;
        ESP_LOGD(TAG, "UART->TCP: %zu bytes", len);
    }
}

/**
 * LED status task
 */
static void led_status_task(void *arg) {
    /* Configure LED pin */
    gpio_reset_pin(STATUS_LED_PIN);
    gpio_set_direction(STATUS_LED_PIN, GPIO_MODE_OUTPUT);

    while (1) {
        if (!wifi_manager_is_connected()) {
            /* Fast blink: not connected to WiFi */
            gpio_set_level(STATUS_LED_PIN, 1);
            vTaskDelay(pdMS_TO_TICKS(100));
            gpio_set_level(STATUS_LED_PIN, 0);
            vTaskDelay(pdMS_TO_TICKS(100));
        } else if (!tcp_server_has_client()) {
            /* Slow blink: WiFi connected, no TCP client */
            gpio_set_level(STATUS_LED_PIN, 1);
            vTaskDelay(pdMS_TO_TICKS(500));
            gpio_set_level(STATUS_LED_PIN, 0);
            vTaskDelay(pdMS_TO_TICKS(500));
        } else {
            /* Solid on: fully connected */
            gpio_set_level(STATUS_LED_PIN, 1);
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
    }
}

/**
 * Stats logging task
 */
static void stats_task(void *arg) {
    uint32_t last_tcp_to_uart = 0;
    uint32_t last_uart_to_tcp = 0;

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(30000)); /* Every 30 seconds */

        if (s_tcp_to_uart_bytes != last_tcp_to_uart ||
            s_uart_to_tcp_bytes != last_uart_to_tcp) {
            ESP_LOGI(TAG, "Stats: TCP->UART=%lu bytes, UART->TCP=%lu bytes",
                     (unsigned long)s_tcp_to_uart_bytes,
                     (unsigned long)s_uart_to_tcp_bytes);
            last_tcp_to_uart = s_tcp_to_uart_bytes;
            last_uart_to_tcp = s_uart_to_tcp_bytes;
        }
    }
}

void app_main(void) {
    ESP_LOGI(TAG, "=================================");
    ESP_LOGI(TAG, "Flipper Zero TCP-UART Bridge");
    ESP_LOGI(TAG, "=================================");
    ESP_LOGI(TAG, "TCP Port: %d", CONFIG_BRIDGE_TCP_PORT);
    ESP_LOGI(TAG, "UART: TX=%d, RX=%d, Baud=%d",
             CONFIG_BRIDGE_UART_TX_PIN,
             CONFIG_BRIDGE_UART_RX_PIN,
             CONFIG_BRIDGE_UART_BAUD_RATE);

    /* Start LED status task */
    xTaskCreate(led_status_task, "led_status", 2048, NULL, 1, NULL);

    /* Initialize WiFi manager */
    ESP_LOGI(TAG, "Initializing WiFi...");
    esp_err_t err = wifi_manager_init();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "WiFi init failed: %s", esp_err_to_name(err));
        return;
    }

    /* Wait for WiFi connection */
    ESP_LOGI(TAG, "Waiting for WiFi connection...");
    while (!wifi_manager_is_connected()) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }

    char ip_str[16];
    wifi_manager_get_ip(ip_str, sizeof(ip_str));
    ESP_LOGI(TAG, "WiFi connected! IP: %s", ip_str);

    /* Initialize UART bridge */
    ESP_LOGI(TAG, "Initializing UART bridge...");
    err = uart_bridge_init(CONFIG_BRIDGE_UART_TX_PIN,
                           CONFIG_BRIDGE_UART_RX_PIN,
                           CONFIG_BRIDGE_UART_BAUD_RATE,
                           on_uart_rx);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "UART init failed: %s", esp_err_to_name(err));
        return;
    }

    /* Initialize TCP server */
    ESP_LOGI(TAG, "Starting TCP server on port %d...", CONFIG_BRIDGE_TCP_PORT);
    err = tcp_server_init(CONFIG_BRIDGE_TCP_PORT, on_tcp_rx);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "TCP server init failed: %s", esp_err_to_name(err));
        return;
    }

    ESP_LOGI(TAG, "=================================");
    ESP_LOGI(TAG, "Bridge ready!");
    ESP_LOGI(TAG, "Connect to: %s:%d", ip_str, CONFIG_BRIDGE_TCP_PORT);
    ESP_LOGI(TAG, "=================================");

    /* Start stats task */
    xTaskCreate(stats_task, "stats", 2048, NULL, 1, NULL);

    /* Main loop - just keep running */
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(10000));

        /* Check WiFi connection and reconnect if needed */
        if (!wifi_manager_is_connected()) {
            ESP_LOGW(TAG, "WiFi connection lost, manager will reconnect...");
        }
    }
}
