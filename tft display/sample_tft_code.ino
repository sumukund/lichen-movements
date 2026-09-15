/*
 * Created by ArduinoGetStarted.com
 *
 * This example code is in the public domain
 *
 * Tutorial page: https://arduinogetstarted.com/tutorials/arduino-round-circular-tft-lcd-display
 */

#include <DIYables_TFT_Round.h>

#define BLACK     DIYables_TFT::colorRGB(0, 0, 0)
#define BLUE      DIYables_TFT::colorRGB(0, 0, 255)
#define RED       DIYables_TFT::colorRGB(255, 0, 0)
#define GREEN     DIYables_TFT::colorRGB(0, 255, 0)
#define ORANGE    DIYables_TFT::colorRGB(255, 165, 0)
#define PINK      DIYables_TFT::colorRGB(255, 192, 203)
#define VIOLET    DIYables_TFT::colorRGB(148, 0, 211)
#define TURQUOISE DIYables_TFT::colorRGB(64, 224, 208)
#define WHITE     DIYables_TFT::colorRGB(255, 255, 255)

#define PIN_RST 8 // The Arduino pin connected to the RST pin of the circular TFT display
#define PIN_DC 9  // The Arduino pin connected to the DC pin of the circular TFT display
#define PIN_CS 10 // The Arduino pin connected to the CS pin of the circular TFT display

DIYables_TFT_GC9A01_Round TFT_display(PIN_RST, PIN_DC, PIN_CS);


void setup() {
  TFT_display.begin();
  TFT_display.setRotation(1); 
}

void looking_side_to_side(int cx, int cy, int radius, uint16_t irisColor, uint16_t pupilColor, int steps, int delayTime) {
    for (int i = 0; i < steps; i++) {
        float angle = -PI / 4 + (PI / 2) * i / (steps - 1); // Move from left to right
        int pupilOffsetX = (radius / 6) * cos(angle);
        int pupilOffsetY = (radius / 6) * sin(angle);
        // Draw the eye with the pupil offset
        // Erase the previous pupil position by drawing over it with the iris color
        int pupilRadius = radius / 4;
        TFT_display.fillCircle(cx + (radius / 6) * cos(-PI / 4 + (PI / 2) * (i - 1) / (steps - 1)), cy + (radius / 6) * sin(-PI / 4 + (PI / 2) * (i - 1) / (steps - 1)), pupilRadius, irisColor);
        // Draw the new pupil position
        TFT_display.fillCircle(cx + pupilOffsetX, cy + pupilOffsetY, pupilRadius, pupilColor);
        delay(delayTime);
    }
}


void blink(int cx, int cy, int radius, uint16_t irisColor, uint16_t pupilColor, int blinkCount, int blinkDuration) {
    for (int i = 0; i < blinkCount; i++) {
        // Draw the eye open
        drawEye(cx, cy, radius, irisColor, pupilColor);
        delay(blinkDuration);

        // Draw the eye closed (just the white part)
        TFT_display.fillCircle(cx, cy, radius, WHITE);
        delay(blinkDuration);
    }
}
void drawEye(int cx, int cy, int radius, uint16_t irisColor, uint16_t pupilColor) {
    // Draw the white part of the eye
    TFT_display.fillCircle(cx, cy, radius, WHITE);

    // Draw the iris
    int irisRadius = radius / 2;
    TFT_display.fillCircle(cx, cy, irisRadius, irisColor);

    // // Draw the pupil
    // int pupilRadius = radius / 4;
    // TFT_display.fillCircle(cx, cy, pupilRadius, pupilColor);
}

void loop() {
    TFT_display.fillScreen(BLACK);

    // Draw an eye at the center of the screen
    drawEye(240, 240, 100, BLUE, BLACK);
    // blink(120, 120, 50, BLUE, BLACK, 3, 200);
    looking_side_to_side(240, 240, 100,, BLUE, BLACK, 20, 500);
}