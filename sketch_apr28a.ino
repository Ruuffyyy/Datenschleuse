#include <Arduino.h>
#include <Wire.h>
#include <lvgl.h>

#include <ESP_IOExpander_Library.h>
#include <ESP_Panel_Library.h>

// ---------------------------
// Waveshare ESP32-S3-Touch-LCD-7
// ---------------------------

// I2C für IO-Expander / Touch laut Waveshare
#define I2C_MASTER_NUM I2C_NUM_0
#define I2C_MASTER_SDA_IO 8
#define I2C_MASTER_SCL_IO 9

// EXIO-Bits laut Waveshare-Dokumentation / Beispielstruktur
#define TP_RST   (1 << 1)   // EXIO1
#define LCD_BL   (1 << 2)   // EXIO2
#define LCD_RST  (1 << 3)   // EXIO3
#define SD_CS    (1 << 4)   // EXIO4
#define USB_SEL  (1 << 5)   // EXIO5

ESP_IOExpander *expander = nullptr;
ESP_Panel *panel = nullptr;
ESP_PanelLcd *lcd = nullptr;
ESP_PanelBacklight *backlight = nullptr;
ESP_PanelTouch *touch = nullptr;

static lv_disp_draw_buf_t draw_buf;
static lv_color_t *buf1 = nullptr;
static lv_color_t *buf2 = nullptr;
static lv_obj_t *label = nullptr;

String serialBuffer;
String screenText;

void initExpander()
{
  expander = new ESP_IOExpander_CH422G(
      (i2c_port_t)I2C_MASTER_NUM,
      ESP_IO_EXPANDER_I2C_CH422G_ADDRESS_000,
      I2C_MASTER_SCL_IO,
      I2C_MASTER_SDA_IO);

  expander->init();
  expander->begin();

  expander->multiPinMode(TP_RST | LCD_BL | LCD_RST | SD_CS | USB_SEL, OUTPUT);

  // Touch Reset / LCD Backlight / LCD Reset / SD deaktivieren
  expander->multiDigitalWrite(TP_RST | LCD_BL | LCD_RST | SD_CS, HIGH);

  // WICHTIG: USB-Modus aktivieren = USB_SEL LOW
  expander->digitalWrite(USB_SEL, LOW);
}

void initDisplay()
{
  panel = new ESP_Panel();
  panel->init();

  lcd = panel->getLcd();
  backlight = panel->getBacklight();
  touch = panel->getTouch();

  lcd->begin();
  lcd->displayOn();

  if (backlight) {
    backlight->begin();
    backlight->on();
  }
}

void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p)
{
  uint32_t w = area->x2 - area->x1 + 1;
  uint32_t h = area->y2 - area->y1 + 1;

  lcd->drawBitmap(area->x1, area->y1, w, h, (uint16_t *)color_p);
  lv_disp_flush_ready(disp);
}

void initLVGL()
{
  lv_init();

  size_t buffer_pixels = 800 * 40;
  buf1 = (lv_color_t *)heap_caps_malloc(buffer_pixels * sizeof(lv_color_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  buf2 = (lv_color_t *)heap_caps_malloc(buffer_pixels * sizeof(lv_color_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);

  lv_disp_draw_buf_init(&draw_buf, buf1, buf2, buffer_pixels);

  static lv_disp_drv_t disp_drv;
  lv_disp_drv_init(&disp_drv);
  disp_drv.hor_res = 800;
  disp_drv.ver_res = 480;
  disp_drv.flush_cb = my_disp_flush;
  disp_drv.draw_buf = &draw_buf;
  lv_disp_drv_register(&disp_drv);
}

void buildUI()
{
  lv_obj_set_style_bg_color(lv_scr_act(), lv_color_hex(0x000000), 0);
  lv_obj_set_style_bg_opa(lv_scr_act(), LV_OPA_COVER, 0);

  lv_obj_t *title = lv_label_create(lv_scr_act());
  lv_label_set_text(title, "USB Monitor vom Raspberry Pi");
  lv_obj_set_style_text_color(title, lv_color_hex(0x00FF88), 0);
  lv_obj_set_style_text_font(title, &lv_font_montserrat_22, 0);
  lv_obj_align(title, LV_ALIGN_TOP_LEFT, 20, 10);

  label = lv_label_create(lv_scr_act());
  lv_obj_set_width(label, 760);
  lv_label_set_long_mode(label, LV_LABEL_LONG_WRAP);
  lv_obj_set_style_text_color(label, lv_color_hex(0xFFFFFF), 0);
  lv_obj_set_style_text_font(label, &lv_font_montserrat_18, 0);
  lv_obj_align(label, LV_ALIGN_TOP_LEFT, 20, 50);
  lv_label_set_text(label, "Warte auf Daten ueber USB-Seriell...");
}

String limitLines(const String &text, int maxLines)
{
  String lines[80];
  int count = 0;
  String current = "";

  for (size_t i = 0; i < text.length(); i++) {
    char c = text[i];
    if (c == '\n') {
      if (count < 80) {
        lines[count++] = current;
      }
      current = "";
    } else {
      current += c;
      if (current.length() >= 52) {
        if (count < 80) {
          lines[count++] = current;
        }
        current = "";
      }
    }
  }

  if (current.length() > 0 && count < 80) {
    lines[count++] = current;
  }

  int start = 0;
  if (count > maxLines) {
    start = count - maxLines;
  }

  String result = "";
  for (int i = start; i < count; i++) {
    result += lines[i];
    if (i < count - 1) result += "\n";
  }

  return result;
}

void updateScreen(const String &msg)
{
  screenText += msg;
  screenText = limitLines(screenText, 18);
  lv_label_set_text(label, screenText.c_str());
}

void handleSerial()
{
  while (Serial.available()) {
    char c = (char)Serial.read();

    if (c == '\r') continue;

    serialBuffer += c;

    if (c == '\n') {
      updateScreen(serialBuffer);
      serialBuffer = "";
    }

    if (serialBuffer.length() > 512) {
      updateScreen(serialBuffer + "\n");
      serialBuffer = "";
    }
  }
}

void setup()
{
  Serial.begin(115200);
  delay(1500);

  Wire.begin(I2C_MASTER_SDA_IO, I2C_MASTER_SCL_IO);

  initExpander();
  initDisplay();
  initLVGL();
  buildUI();

  updateScreen("Display gestartet\n");
  updateScreen("USB-Seriell bereit\n");
}

void loop()
{
  handleSerial();
  lv_timer_handler();
  delay(5);
}