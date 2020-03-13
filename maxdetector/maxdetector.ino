#define PIN_BUTTON (1 << 0)
#define PIN_LED (1 << 5)
#define PIN_SIGNAL (1 << 2)

#define PIN_BUZZER 11

#define BUTTON_PRESSED  0b11000000
#define BUTTON_RELEASED 0b00000111
#define BUTTON_MASK     0b11000111

uint8_t button_history = 0;
uint8_t keydown = 0;
unsigned long last_update = 0;
unsigned long last_tone_change = 0;
uint8_t silent_mode = 0;
uint8_t state = 0;
uint16_t degree = 0;

void setup() {
  DDRB = PIN_LED | PIN_BUZZER;
  PORTB |= PIN_BUTTON;

  Serial.begin(115200);
  Serial.write("Started.\r\n");
  Serial.write("\r\n");
}

void loop() {
  unsigned long now = millis();

  // This ensures that activating silent mode cancels the buzzer immediately.
  if (silent_mode)
    noTone(PIN_BUZZER);

  if (state == 0) {
    if (PINB & PIN_SIGNAL) {
      Serial.write("Alarm activated.\r\n");
      PORTB |= PIN_LED;
      state = 1;
    }
  } else if (state == 1) {
    if (! (PINB & PIN_SIGNAL)) {
      Serial.write("Alarm deactivated.\r\n");
      PORTB &= ~(PIN_LED);
      noTone(PIN_BUZZER);
      state = 0;
    } else {
      if (! silent_mode && (now - last_tone_change) > 10) {
        last_tone_change = now;
        float radian = (degree * 71) / 4068.0;
        int freq = int(1000 + sin(radian) * 1000);
        degree = (degree + 1) % 180;
        /*
          Serial.write("F:");
          Serial.print(degree);
          Serial.write(':');
          Serial.print(freq);
          Serial.write("\r\n");
        */
        tone(PIN_BUZZER, freq);
      }
    }
  }

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
}
