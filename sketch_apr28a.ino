#include <Arduino.h>
#include <Arduino_GFX_Library.h>
#include <vector>

Arduino_ESP32RGBPanel *bus = new Arduino_ESP32RGBPanel(
    46 /* CSYNC */, 3 /* VSYNC */, 5 /* DE */, 7 /* PCLK */,
    1 /* R3 */, 2 /* R4 */, 42 /* R5 */, 41 /* R6 */, 40 /* R7 */,
    14 /* G0 */, 39 /* G1 */, 45 /* G2 */, 48 /* G3 */, 47 /* G4 */, 21 /* G5 */,
    10 /* B3 */, 38 /* B4 */, 18 /* B5 */, 17 /* B6 */, 16 /* B7 */,
    0 /* hsync_polarity */, 8 /* hsync_front_porch */, 4 /* hsync_pulse_width */, 43 /* hsync_back_porch */,
    0 /* vsync_polarity */, 8 /* vsync_front_porch */, 4 /* vsync_pulse_width */, 12 /* vsync_back_porch */
);

Arduino_RPi_DPI_RGBPanel *gfx = new Arduino_RPi_DPI_RGBPanel(
    bus,
    800 /* width */,
    480 /* height */,
    0 /* rotation */,
    true /* auto_flush */
);

String incomingText = "";
std::vector<String> lines;

void redrawScreen() {
  gfx->fillScreen(BLACK);
  gfx->setTextSize(2);
  gfx->setTextColor(WHITE);
  gfx->setCursor(10, 10);
  gfx->println("USB Monitor Ausgabe");

  int y = 40;
  for (size_t i = 0; i < lines.size(); i++) {
    gfx->setCursor(10, y);
    gfx->println(lines[i]);
    y += 22;
    if (y > 460) break;
  }
}

void setTextAsLines(const String &text) {
  lines.clear();
  String current = "";

  for (size_t i = 0; i < text.length(); i++) {
    char c = text[i];
    if (c == '\n') {
      lines.push_back(current);
      current = "";
    } else {
      current += c;
      if (current.length() > 48) {
        lines.push_back(current);
        current = "";
      }
    }
  }

  if (current.length() > 0) {
    lines.push_back(current);
  }

  if (lines.size() > 18) {
    lines.erase(lines.begin(), lines.begin() + (lines.size() - 18));
  }
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  if (!gfx->begin()) {
    Serial.println("Display init fehlgeschlagen");
    return;
  }

  gfx->fillScreen(BLACK);
  gfx->setTextColor(GREEN);
  gfx->setTextSize(2);
  gfx->setCursor(10, 10);
  gfx->println("Warte auf Daten vom Pi...");
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    incomingText += c;

    if (incomingText.length() > 3000) {
      incomingText.remove(0, 1000);
    }

    if (c == '\n') {
      setTextAsLines(incomingText);
      redrawScreen();
    }
  }
}