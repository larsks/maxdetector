#define PIN_BUTTON      (1 << 0)    // D8
#define PIN_SIGNAL      (1 << 2)    // D10
#define PIN_BELL        (1 << 4)    // D12

#define PIN_LED_POWER   (1 << 5)    // D5
#define PIN_LED_SILENT  (1 << 6)    // D6
#define PIN_LED_ALARM   (1 << 7)    // D7

#define BUTTON_PRESSED  0b11000000
#define BUTTON_RELEASED 0b00000111
#define BUTTON_MASK     0b11000111

#define NUM_BELLS 3

typedef unsigned long time_t;

uint8_t button_history = 0;
int keydown = 0;
time_t last_update = 0;
time_t last_tone_change = 0;
int silent_mode = 0;
int state = 0;
int bells = NUM_BELLS;

void setup() {
  DDRB = PIN_BELL;
  DDRD = PIN_LED_POWER|PIN_LED_SILENT|PIN_LED_ALARM;

  // set pull-up on button input
  PORTB |= PIN_BUTTON;

  // ensure bell is off
  PORTB |= PIN_BELL;

  // ensure power LED is on, others are off
  PORTD = PIN_LED_POWER;

  Serial.begin(115200);
  Serial.write("Started.\r\n");
  Serial.write("\r\n");
}

void loop() {
  time_t now = millis();

  // This ensures that activating silent mode cancels the alarm immediately.
  if (silent_mode) {
    PORTB |= PIN_BELL;
    PORTD |= PIN_LED_SILENT;
  } else {
    PORTD &= ~(PIN_LED_SILENT);
  }

  if (state == 0) {
    if (PINB & PIN_SIGNAL) {
      Serial.write("Alarm activated.\r\n");
      PORTD |= PIN_LED_ALARM;
      state = 1;
      bells = NUM_BELLS;
    }
  } else if (state == 1) {
    if (! (PINB & PIN_SIGNAL)) {
      Serial.write("Alarm deactivated.\r\n");
      PORTD &= ~(PIN_LED_ALARM);
      PORTB |= PIN_BELL;
      state = 0;
    } else if (silent_mode) {
      // do nothing
    } else {
      if (now - last_tone_change > 1000) {
        Serial.write("Ding.\r\n");
        last_tone_change = now;
        PORTB ^= PIN_BELL;
        if ((--bells) < 0)
          state = 2;
      }
    }
  } else if (state == 2) {
    PORTB |= PIN_BELL;

    if (! (PINB & PIN_SIGNAL)) {
      Serial.write("Alarm deactivated.\r\n");
      PORTD &= ~(PIN_LED_ALARM);
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
