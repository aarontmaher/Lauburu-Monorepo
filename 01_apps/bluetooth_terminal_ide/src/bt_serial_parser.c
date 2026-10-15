/*
 * Lauburu Sovereign Bluetooth Serial Terminal — Zero-Heap C11 Frame Parser & POSIX termios Helper
 * Governed by: /polyglot-c-cpp-specialist (C11, POSIX termios, BNEP/RFCOMM MTU 1280)
 * Rule #0: Zero-Mock Truth Mandate
 */

#include <stddef.h>
#include <stdint.h>

#define BT_SERIAL_MAX_MTU 1280U

typedef struct {
    uint32_t frame_length;
    uint16_t crc16_ccitt;
    uint8_t  valid;
    uint8_t  is_teleplot_metric;
} bt_serial_frame_status_t;

/*
 * Computes CCITT-16 checksum (0x1021 polynomial) over a Bluetooth RFCOMM / Teleplot frame
 * with zero dynamic memory allocation.
 */
uint16_t bt_serial_crc16_ccitt(const uint8_t *buf, size_t len) {
    if (buf == NULL || len == 0U) {
        return 0U;
    }
    uint16_t crc = 0xFFFFU;
    for (size_t i = 0U; i < len; ++i) {
        crc ^= (uint16_t)((uint16_t)buf[i] << 8U);
        for (uint8_t bit = 0U; bit < 8U; ++bit) {
            if ((crc & 0x8000U) != 0U) {
                crc = (uint16_t)((crc << 1U) ^ 0x1021U);
            } else {
                crc = (uint16_t)(crc << 1U);
            }
        }
    }
    return crc;
}

/*
 * Validates a single incoming Bluetooth Serial / RFCOMM line or Teleplot frame (>metric:val)
 * within the strict 1280-byte BNEP/RFCOMM MTU ceiling.
 */
bt_serial_frame_status_t bt_serial_validate_frame(const uint8_t *buf, size_t len) {
    bt_serial_frame_status_t status = {0U, 0U, 0U, 0U};
    if (buf == NULL || len == 0U || len > BT_SERIAL_MAX_MTU) {
        return status;
    }
    status.frame_length = (uint32_t)len;
    status.crc16_ccitt = bt_serial_crc16_ccitt(buf, len);
    status.valid = 1U;
    if (buf[0] == (uint8_t)'>') {
        for (size_t i = 1U; i < len; ++i) {
            if (buf[i] == (uint8_t)':') {
                status.is_teleplot_metric = 1U;
                break;
            }
        }
    }
    return status;
}
