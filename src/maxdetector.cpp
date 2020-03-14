#include "Arduino.h"

#define PIN_BUTTON      (1 << 0)    // D8
#define PIN_SIGNAL      (1 << 2)    // D10
#define PIN_READY       (1 << 3)    // D11
#define PIN_BELL        (1 << 4)    // D12

#define PIN_LED_POWER   (1 << 5)    // D5
#define PIN_LED_SILENT  (1 << 6)    // D6
#define PIN_LED_ALARM   (1 << 7)    // D7

#define WIFI_READY (!(PINB & PIN_READY))
#define WIFI_NOT_READY (PINB & PIN_READY)

#define ALARM_ACTIVE (!(PINB & PIN_SIGNAL))
#define ALARM_INACTIVE (PINB & PIN_SIGNAL)

#define BUTTON_PRESSED  0b11000000
#define BUTTON_RELEASED 0b00000111
#define BUTTON_MASK     0b11000111
#define BUTTON_DOWN     0b00000000
#define BUTTON_UP       0b11111111

#define NUM_BELLS 2
#define BELL_DURATION 500
#define BELL_INTERVAL_1 1000U           // 1 second
#define BELL_INTERVAL_2 (1000U * 300U)  // 5 minutes
#define COOLDOWN_INTERVAL 10000U        // 10 seconds

#define STATE_WAIT_READY    0
#define STATE_IDLE          1
#define STATE_ALARM_1       2
#define STATE_ALARM_2       3
#define STATE_ALARM_3       4
#define STATE_COOLDOWN_1    5
#define STATE_COOLDOWN_2    6

typedef unsigned long time_t;

uint8_t button_history = 0;
int keydown            = 0;
time_t last_update     = 0;
time_t last_bell       = 0;
time_t cooldown_start  = 0;
int silent_mode        = 0;
int state              = 0;
int bells              = NUM_BELLS;

void setup() {
    // configure outputs
    DDRB = PIN_BELL;
    DDRD = PIN_LED_POWER|PIN_LED_SILENT|PIN_LED_ALARM;

    // set pull-up on inputs
    PORTB |= PIN_BUTTON|PIN_READY|PIN_SIGNAL;

    // ensure bell relay is off
    PORTB |= PIN_BELL;

    // ensure power LED is on, others are off
    PORTD = PIN_LED_POWER;

    Serial.begin(115200);
    Serial.write("Started.\r\n");
    Serial.write("\r\n");
}

void loop() {
    time_t now = millis();

    // light LED_SILENT in silent mode
    if (silent_mode) {
        PORTD |= PIN_LED_SILENT;
    } else {
        PORTD &= ~(PIN_LED_SILENT);
    }

    // finish pending bell
    if ((now - last_bell) >= BELL_DURATION)
        PORTB |= PIN_BELL;

    // handle silent mode button
    if (now - last_update > 10) {
        last_update = now;
        button_history = button_history << 1;
        button_history |= (PINB & PIN_BUTTON) ? 1 : 0;

        if ((button_history & BUTTON_MASK) == BUTTON_PRESSED) {
            keydown = 1;
        } else if (keydown && (button_history & BUTTON_MASK) == BUTTON_RELEASED) {
            keydown = 0;
            silent_mode = !silent_mode;
            Serial.write("Toggle silent mode: ");
            Serial.print(silent_mode);
            Serial.write("\r\n");
        }
    }

    switch (state) {

        // Wait for the READY signal from the ESP8266.
        case STATE_WAIT_READY:
            PORTD &= ~(PIN_LED_ALARM);

            if (WIFI_READY) {
                Serial.write("WiFi is ready.\r\n");
                state = STATE_IDLE;
            }
            break;

        // Wait for the ESP8266 to tell us it has found a target
        // BSSID by raising the ALARM signal.
        case STATE_IDLE:
            if (WIFI_NOT_READY) {
                Serial.write("WiFi is not ready.\r\n");
                state = STATE_WAIT_READY;
            } else if (ALARM_ACTIVE) {
                Serial.write("Alarm activated.\r\n");
                state = STATE_ALARM_1;
            }

            break;

        // Light LED_ALARM and initialize the bell counter.
        case STATE_ALARM_1:
            PORTD |= PIN_LED_ALARM;
            bells = NUM_BELLS;
            state = STATE_ALARM_2;
            break;

        // Sound the bell.
        case STATE_ALARM_2:
            if (WIFI_NOT_READY) {
                Serial.write("WiFi is not ready.\r\n");
                state = STATE_WAIT_READY;
            } else if (ALARM_INACTIVE) {
                Serial.write("Alarm deactivated.\r\n");
                PORTD &= ~(PIN_LED_ALARM);
                state = STATE_COOLDOWN_1;
            } else if ((now - last_bell) > BELL_INTERVAL_1) {
                Serial.write("Ding.\r\n");
                last_bell = now;
                if (! silent_mode)
                    PORTB &= ~(PIN_BELL);

                if (! (--bells)) {
                    Serial.write("Initial bell finished.\r\n");
                    state = STATE_ALARM_3;
                }
            }

            break;

        // Sound the bell at longer intervals.
        case STATE_ALARM_3:
            if (WIFI_NOT_READY) {
                Serial.write("WiFi is not ready.\r\n");
                state = STATE_WAIT_READY;
            } else if (ALARM_INACTIVE) {
                Serial.write("Alarm deactivated.\r\n");
                PORTD &= ~(PIN_LED_ALARM);
                state = STATE_COOLDOWN_1;
            } else if ((now - last_bell) > BELL_INTERVAL_2) {
                Serial.write("Ding.\r\n");
                last_bell = now;
                if (! silent_mode)
                    PORTB &= ~(PIN_BELL);
            }

            break;

        // Initialize cooldown timer.
        case STATE_COOLDOWN_1:
            Serial.write("Cooldown start.\r\n");
            cooldown_start = now;
            state = STATE_COOLDOWN_2;
            break;

        // Wait for cooldown timer to expire.
        case STATE_COOLDOWN_2:
            if (WIFI_NOT_READY) {
                Serial.write("WiFi is not ready.\r\n");
                state = STATE_WAIT_READY;
            } else if (now - cooldown_start >= COOLDOWN_INTERVAL) {
                Serial.write("Cooldown complete.\r\n");
                state = STATE_IDLE;
            }
            break;
    }
}
