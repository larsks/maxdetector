#define PIN_BUTTON (1 << 0)
#define PIN_LED (1 << 5)
#define PIN_SIGNAL (1 << 2)
#define PIN_BELL (1 << 4)

#define PIN_BUZZER 11

#define BUTTON_PRESSED  0b11000000
#define BUTTON_RELEASED 0b00000111
#define BUTTON_MASK     0b11000111

#define NUM_BELLS 3

uint8_t button_history = 0;
int keydown = 0;
unsigned long last_update = 0;
unsigned long last_tone_change = 0;
int silent_mode = 0;
int state = 0;
int bells = NUM_BELLS;

void setup() {
  DDRB = PIN_LED | PIN_BELL;

  // set pull-up on button input
  PORTB |= PIN_BUTTON;

  // ensure bell is off
  PORTB |= PIN_BELL;

  Serial.begin(115200);
  Serial.write("Started.\r\n");
  Serial.write("\r\n");
}

void loop() {
  unsigned long now = millis();

  // This ensures that activating silent mode cancels the buzzer immediately.
  if (silent_mode)
    PORTB |= PIN_BELL;

  if (state == 0) {
    if (PINB & PIN_SIGNAL) {
      Serial.write("Alarm activated.\r\n");
      PORTB |= PIN_LED;
      state = 1;
      bells = NUM_BELLS;
    }
  } else if (state == 1) {
    if (! (PINB & PIN_SIGNAL)) {
      Serial.write("Alarm deactivated.\r\n");
      PORTB &= ~(PIN_LED);
      PORTB |= PIN_BELL;
      state = 0;
    } else if (silent_mode) {
      // do nothing
    } else {
      if (now - last_tone_change > 1000) {
        Serial.write("Ding.\r\n");
        last_tone_change = now;
        PORTB ^= PIN_BELL;
        if (! bells--)
          state = 2;
      }
    }
  } else if (state == 2) {
    PORTB |= PIN_BELL;

    if (! (PINB & PIN_SIGNAL)) {
      Serial.write("Alarm deactivated.\r\n");
      PORTB &= ~(PIN_LED);
      state = 0;
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
