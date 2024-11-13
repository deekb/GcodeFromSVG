#include <MeAuriga.h>
#include <AccelStepper.h>
#include "laser.h"

// Stepper motor settings
#define MOTOR_INTERFACE_TYPE 1
#define STEPPER_MAX_ACHIEVABLE_SPEED 1500
#define TIME_TO_MAX_SPEED_SECONDS 0.1

#define X_STEP_PIN 4
#define X_DIR_PIN 5
#define Y_STEP_PIN 2
#define Y_DIR_PIN 3

// Laser settings
#define LASER_PWM 11
#define DRIVER_H1 48
#define DRIVER_H2 49

// Create instances of AccelStepper
AccelStepper xStepper = AccelStepper(MOTOR_INTERFACE_TYPE, X_STEP_PIN, X_DIR_PIN);
AccelStepper yStepper = AccelStepper(MOTOR_INTERFACE_TYPE, Y_STEP_PIN, Y_DIR_PIN);

// Instantiate the Laser class
Laser laser(LASER_PWM, DRIVER_H1, DRIVER_H2);

MePort limitSwitchesX(PORT_10);
int xlimit_pin1 = limitSwitchesX.pin1();  // +X limit
int xlimit_pin2 = limitSwitchesX.pin2();  // -X limit

MePort limitSwitchesY(PORT_8);
int ylimit_pin1 = limitSwitchesY.pin1();  // +Y limit
int ylimit_pin2 = limitSwitchesY.pin2();  // -Y limit

float DESIRED_MAX_SPEED = STEPPER_MAX_ACHIEVABLE_SPEED;

// Variables for G-code parsing
String command = "";
long xPos = 0, yPos = 0;

void setup() {
  Serial.begin(1000000);

  // Set up limit switches as input with pull-up resistors
  pinMode(ylimit_pin1, INPUT_PULLUP);
  pinMode(ylimit_pin2, INPUT_PULLUP);
  pinMode(xlimit_pin1, INPUT_PULLUP);
  pinMode(xlimit_pin2, INPUT_PULLUP);

  // Initialize the laser
  laser.begin();

  // Calculate acceleration based on desired time and max speed
  float acceleration = (DESIRED_MAX_SPEED * DESIRED_MAX_SPEED) / (2.0f * TIME_TO_MAX_SPEED_SECONDS);

  // Set maximum speed and calculated acceleration for the steppers
  xStepper.setMaxSpeed(DESIRED_MAX_SPEED);
  yStepper.setMaxSpeed(DESIRED_MAX_SPEED);
  xStepper.setAcceleration(acceleration);
  yStepper.setAcceleration(acceleration);

  // Set the initial positions
  xStepper.setCurrentPosition(0);
  yStepper.setCurrentPosition(0);
}

void loop() {
  // Check if data is available in the serial buffer
  if (Serial.available()) {
    char c = Serial.read();

    // Build the command string
    if (c == '\n') {
      // Parse the command when a newline character is received
      parseGCode(command);
      command = "";  // Reset command after parsing
    } else {
      command += c;  // Append character to the command string
    }
  }
}

// Homing logic for a specific axis
void homeAxis(AccelStepper& stepper, int limitPin, int backoffDistance, int speed) {
  stepper.setSpeed(speed);  // Slow speed for homing

  // Move towards the limit switch
  stepper.moveTo(-100000);  // Move a large number of steps towards the limit switch

  // Keep moving until the limit switch is triggered
  while (digitalRead(limitPin) == HIGH) {
    stepper.runSpeed();
  }

  // Stop the stepper and back off
  stepper.stop();
  stepper.move(backoffDistance);  // Move back by the backoff distance
  while (stepper.distanceToGo() != 0) {
    stepper.runSpeed();
  }

  // Set the current position to 0 (home position)
  stepper.setCurrentPosition(0);
}


// G-code parser
void parseGCode(String gcode) {
  gcode.trim();  // Remove any leading/trailing whitespace

  // Current positions
  float targetX = xPos;  // X position
  float targetY = yPos;  // Y position

  // Extract command type (e.g., G0, G1, M4, G28, M119)
  int index = gcode.indexOf(' ');
  String commandType = (index != -1) ? gcode.substring(0, index) : gcode;

  // G0/G1 movement commands
  if (commandType == "G0" || commandType == "G1") {
    int xIndex = gcode.indexOf('X');
    int yIndex = gcode.indexOf('Y');

    if (xIndex != -1) {
      // Parse X value and update targetX
      int endIndex = gcode.indexOf(' ', xIndex);
      if (endIndex == -1) endIndex = gcode.length();
      targetX = gcode.substring(xIndex + 1, endIndex).toFloat();
    }

    if (yIndex != -1) {
      // Parse Y value and update targetY
      int endIndex = gcode.indexOf(' ', yIndex);
      if (endIndex == -1) endIndex = gcode.length();
      targetY = gcode.substring(yIndex + 1, endIndex).toFloat();
    }

    xStepper.setSpeed(DESIRED_MAX_SPEED);
    yStepper.setSpeed(DESIRED_MAX_SPEED);

    // Set target positions for the steppers
    xStepper.moveTo(targetX * 10.0);
    yStepper.moveTo(targetY * 10.0);

    // Move steppers to the target positions
    while (xStepper.distanceToGo() != 0 || yStepper.distanceToGo() != 0) {
      xStepper.runSpeedToPosition();
      yStepper.runSpeedToPosition();
    }

    // Update current positions
    xPos = targetX;
    yPos = targetY;
  }
  // M4 command for setting laser power
  else if (commandType == "M4") {
    int sIndex = gcode.indexOf('S');

    if (sIndex != -1) {
      // Parse S value (laser power)
      int endIndex = gcode.indexOf(' ', sIndex);
      if (endIndex == -1) endIndex = gcode.length();

      int power = gcode.substring(sIndex + 1, endIndex).toInt();
      power = constrain(power, 0, 255);  // Constrain power between 0-255

      // Set the laser power
      laser.setPower(power);
      Serial.println("Laser power set to: " + String(power));
    }
  }
  // G28 command for homing
  else if (commandType == "G28") {
    bool homeX = gcode.indexOf('X') != -1;
    bool homeY = gcode.indexOf('Y') != -1;

    if (!homeX && !homeY) {  // If no axis is specified, home both
      homeX = true;
      homeY = true;
    }

    if (homeX) {
      homeAxis(xStepper, xlimit_pin2, 200, DESIRED_MAX_SPEED);
      homeAxis(xStepper, xlimit_pin2, 0, 150);
    }
    if (homeY) {
      homeAxis(yStepper, ylimit_pin2, 200, DESIRED_MAX_SPEED);
      homeAxis(yStepper, ylimit_pin2, 0, 150);
    }

    Serial.println("Homing completed.");
  }
  // M119 command for reporting limit switch states
  else if (commandType == "M119") {
    reportLimitSwitchStates();
  }
  // Unrecognized command
  else {
    Serial.println("Unknown GCODE: " + commandType);
  }

  // Acknowledge completion
  Serial.println("OK");
}

// Report limit switch states (M119)
void reportLimitSwitchStates() {
  int xLimitMin = digitalRead(xlimit_pin2);  // -X limit switch
  int xLimitMax = digitalRead(xlimit_pin1);  // +X limit switch
  int yLimitMin = digitalRead(ylimit_pin2);  // -Y limit switch
  int yLimitMax = digitalRead(ylimit_pin1);  // +Y limit switch

  // Report X-axis limit switch status
  Serial.print("X Min (-X limit): ");
  Serial.println(xLimitMin == LOW ? "Triggered" : "Open");
  Serial.print("X Max (+X limit): ");
  Serial.println(xLimitMax == LOW ? "Triggered" : "Open");

  // Report Y-axis limit switch status
  Serial.print("Y Min (-Y limit): ");
  Serial.println(yLimitMin == LOW ? "Triggered" : "Open");
  Serial.print("Y Max (+Y limit): ");
  Serial.println(yLimitMax == LOW ? "Triggered" : "Open");
}
