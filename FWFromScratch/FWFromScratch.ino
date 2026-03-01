#include <AccelStepper.h>

#define MOTOR_INTERFACE_TYPE 1  // 1 for Driver mode (uses STEP and DIR pins)
#define STEPPER_MAX_ACHIEVABLE_SPEED 2000
#define TIME_TO_MAX_SPEED_SECONDS 0.01

#define X_STEP_PIN 4
#define X_DIR_PIN 5

#define Y_STEP_PIN 2
#define Y_DIR_PIN 3


#include <Servo.h>

Servo myServo;  // Create a Servo object


// Create an instance of the AccelStepper library
AccelStepper xStepper = AccelStepper(MOTOR_INTERFACE_TYPE, X_STEP_PIN, X_DIR_PIN);
AccelStepper yStepper = AccelStepper(MOTOR_INTERFACE_TYPE, Y_STEP_PIN, Y_DIR_PIN);

float DESIRED_MAX_SPEED = STEPPER_MAX_ACHIEVABLE_SPEED;

// Variables for G-code parsing
String command = "";
float xPos = 0, yPos = 0;

void setup() {
  Serial.begin(1000000);

  // Calculate acceleration based on desired time and max speed
  float acceleration = (DESIRED_MAX_SPEED * DESIRED_MAX_SPEED) / (2.0f * TIME_TO_MAX_SPEED_SECONDS);

  // Set maximum speed and calculated acceleration
  xStepper.setMaxSpeed(DESIRED_MAX_SPEED);
  yStepper.setMaxSpeed(DESIRED_MAX_SPEED);
  xStepper.setAcceleration(acceleration);
  yStepper.setAcceleration(acceleration);

  // Set the initial positions
  xStepper.setCurrentPosition(0);
  yStepper.setCurrentPosition(0);

  myServo.attach(A9);  // Attach servo to pin A9
}

void loop() {
  // Check if data is available in the serial buffer
  if (Serial.available()) {
    char c = Serial.read();
    
    // Build the command string
    if (c == '\n') {
      // Parse the command when a newline character is received
      parseGCode(command);
      command = "";
    } else {
      command += c;
    }
  }

    // Replace the while loop in parseGCode with:
   while (xStepper.distanceToGo() != 0 || yStepper.distanceToGo() != 0) {
      xStepper.runSpeedToPosition();
      yStepper.runSpeedToPosition();
  }
}

void parseGCode(String gcode) {
  float targetX = xPos;
  float targetY = yPos;

  // Split the G-code command into tokens
  int index = gcode.indexOf(' ');
  String commandType = gcode.substring(0, index);
  
  // Process G0 or G1 commands
  if (commandType == "G0" || commandType == "G1") {
    int xIndex = gcode.indexOf('X');
    int yIndex = gcode.indexOf('Y');

    if (xIndex != -1) {
      targetX = gcode.substring(xIndex + 1, gcode.indexOf(' ', xIndex)).toFloat();
    }
    if (yIndex != -1) {
      targetY = gcode.substring(yIndex + 1, gcode.indexOf(' ', yIndex)).toFloat();
    }

    // Set the target positions for the steppers
    xStepper.moveTo(targetX * 10.0);
    yStepper.moveTo(targetY * 10.0);
     while (xStepper.distanceToGo() != 0 || yStepper.distanceToGo() != 0) {
      xStepper.runSpeedToPosition();
      yStepper.runSpeedToPosition();
  }
  } 
  // Process M4 command with power (0-255) as S parameter
  else if (commandType == "M4") {
    int sIndex = gcode.indexOf('S');
    if (sIndex != -1) {
      int spaceIndex = gcode.indexOf(' ', sIndex);
      if (spaceIndex == -1) spaceIndex = gcode.length();
      int power = gcode.substring(sIndex + 1, spaceIndex).toInt();
      // Ensure power is within the range 0-255
      power = constrain(power, 0, 255);
      if (power == 0) {
        myServo.write(30);
      } else {
        myServo.write(23);
      }
      Serial.print("M4 command received with power: ");
      Serial.println(power);
    } else {
      Serial.println("M4 command received with no power specified");
    }
  } else {
    Serial.print(commandType);
    Serial.println(" command received but not implemented");
  }
  
  Serial.println("OK");
}
