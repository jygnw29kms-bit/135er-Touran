#include "touran_gateway.h"

#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "driver/usb_serial_jtag.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#define GATEWAY_FW "0.4.0-usb-weekend-ro"
#define TX_QUEUE_DEPTH 96
#define TX_LINE_MAX 256
#define RX_LINE_MAX 768

static const char *TAG = "touran_gateway";

typedef struct {
    uint16_t len;
    char data[TX_LINE_MAX];
} gateway_tx_t;

static QueueHandle_t s_tx_queue;
static volatile bool s_capture = true;
static volatile uint64_t s_can1_rx = 0;
static volatile uint64_t s_can2_rx = 0;
static volatile uint64_t s_drops = 0;
static volatile uint64_t s_usb_tx = 0;
static volatile uint64_t s_usb_rx = 0;

static bool queue_line(const char *line)
{
    if (!line || !s_tx_queue) return false;
    size_t len = strlen(line);
    if (len == 0 || len >= TX_LINE_MAX) {
        s_drops++;
        return false;
    }
    gateway_tx_t msg = { .len = (uint16_t)len };
    memcpy(msg.data, line, len + 1);
    if (xQueueSend(s_tx_queue, &msg, 0) != pdTRUE) {
        s_drops++;
        return false;
    }
    return true;
}

static void send_hello(void)
{
    char line[256];
    snprintf(line, sizeof(line),
             "{\"type\":\"hello\",\"proto\":1,\"device\":\"135er-touran-gateway\","
             "\"board\":\"ESP32-S3-CAN-2CH-U\",\"fw\":\"%s\",\"transport\":\"usb-serial-jtag\","
             "\"readonly\":true,\"tx_hard_blocked\":true,\"wifi\":false,"
             "\"profile\":\"touran-weekend-capture\"}\n", GATEWAY_FW);
    queue_line(line);
}

static void send_health(void)
{
    char line[384];
    snprintf(line, sizeof(line),
             "{\"type\":\"health\",\"uptime_ms\":%" PRIu64 ",\"can1_rate\":500,"
             "\"can2_rate\":100,\"readonly\":true,\"tx_hard_blocked\":true,\"wifi\":false,"
             "\"transport\":\"usb-serial-jtag\",\"can1_rx\":%" PRIu64 ",\"can2_rx\":%" PRIu64 ","
             "\"usb_tx\":%" PRIu64 ",\"usb_rx\":%" PRIu64 ",\"drops\":%" PRIu64 "}\n",
             (uint64_t)(esp_timer_get_time() / 1000), s_can1_rx, s_can2_rx, s_usb_tx, s_usb_rx, s_drops);
    queue_line(line);
}

void touran_gateway_can_frame(uint8_t channel, uint32_t can_id,
                              const uint8_t *data, uint8_t len, bool extd)
{
    if (channel == 1) s_can1_rx++;
    else if (channel == 2) s_can2_rx++;
    if (!s_capture) return;

    char hex[17] = {0};
    size_t pos = 0;
    if (len > 8) len = 8;
    for (uint8_t i = 0; i < len && pos + 2 < sizeof(hex); i++) {
        pos += (size_t)snprintf(hex + pos, sizeof(hex) - pos, "%02X", data[i]);
    }

    char line[192];
    snprintf(line, sizeof(line),
             "{\"type\":\"can\",\"ch\":%u,\"ts_us\":%" PRIi64 ",\"id\":%" PRIu32 ","
             "\"ext\":%s,\"data\":\"%s\"}\n",
             channel, esp_timer_get_time(), can_id, extd ? "true" : "false", hex);
    (void)queue_line(line);
}

static void handle_command(const char *line)
{
    if (!line) return;
    if (strstr(line, "\"cmd\":\"hello\"")) {
        send_hello();
    } else if (strstr(line, "\"cmd\":\"health\"")) {
        send_health();
    } else if (strstr(line, "\"cmd\":\"capture\"")) {
        s_capture = strstr(line, "\"enable\":false") == NULL;
    } else if (strstr(line, "\"cmd\":\"diag_request\"") ||
               strstr(line, "\"cmd\":\"mfa_send\"") ||
               strstr(line, "\"cmd\":\"mfa_nav\"") ||
               strstr(line, "\"cmd\":\"mfa_compass\"") ||
               strstr(line, "\"cmd\":\"set_mode\"") ||
               strstr(line, "\"cmd\":\"ota\"")) {
        queue_line("{\"type\":\"error\",\"code\":\"READ_ONLY\",\"message\":\"active CAN transmit disabled\"}\n");
    }
}

static void gateway_usb_task(void *arg)
{
    (void)arg;
    usb_serial_jtag_driver_config_t cfg = {
        .tx_buffer_size = 4096,
        .rx_buffer_size = 2048,
    };
    esp_err_t err = usb_serial_jtag_driver_install(&cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "USB Serial/JTAG install failed: %s", esp_err_to_name(err));
        vTaskDelete(NULL);
        return;
    }

    ESP_LOGI(TAG, "USB Serial/JTAG gateway ready; Wi-Fi disabled");
    send_hello();
    send_health();

    char rx[256];
    char line[RX_LINE_MAX];
    size_t used = 0;
    bool oversized = false;

    while (1) {
        gateway_tx_t msg;
        while (xQueueReceive(s_tx_queue, &msg, 0) == pdTRUE) {
            int written = usb_serial_jtag_write_bytes((const uint8_t *)msg.data, msg.len, pdMS_TO_TICKS(10));
            if (written == msg.len) s_usb_tx++;
            else s_drops++;
        }

        int n = usb_serial_jtag_read_bytes((uint8_t *)rx, sizeof(rx), pdMS_TO_TICKS(10));
        if (n > 0) {
            s_usb_rx += (uint64_t)n;
            for (int i = 0; i < n; i++) {
                char c = rx[i];
                if (c == '\n') {
                    line[used] = '\0';
                    if (!oversized && used > 0) handle_command(line);
                    used = 0;
                    oversized = false;
                } else if (c != '\r' && !oversized) {
                    if (used + 1 < sizeof(line)) line[used++] = c;
                    else { used = 0; oversized = true; s_drops++; }
                }
            }
        }
    }
}

esp_err_t touran_gateway_start(void)
{
    if (!s_tx_queue) s_tx_queue = xQueueCreate(TX_QUEUE_DEPTH, sizeof(gateway_tx_t));
    if (!s_tx_queue) return ESP_ERR_NO_MEM;
    BaseType_t ok = xTaskCreatePinnedToCore(gateway_usb_task, "touran_usb", 6144, NULL, 5, NULL, 1);
    return ok == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}
