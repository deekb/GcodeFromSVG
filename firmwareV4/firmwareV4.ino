#include <MeAuriga.h>
#include "laser.h"

#define STEPPER_X_FORWARD -1
#define STEPPER_X_BACKWARD 1
#define STEPPER_Y_FORWARD -1
#define STEPPER_Y_BACKWARD 1

float currentX, currentY;
float targetX, targetY;

int targetXStepperPosition, targetYStepperPosition;
int currentXStepperPosition, currentYStepperPosition;

// Steppers
MePort stepperX(PORT_1);
MePort stepperY(PORT_2);


//Limit switches
MePort limitSwitchesX(PORT_6);
int xlimit_pin1 = limitSwitchesX.pin1();  //limit 4
int xlimit_pin2 = limitSwitchesX.pin2();  //limit 3

MePort limitSwitchesY(PORT_8);
int ylimit_pin1 = limitSwitchesY.pin1();  //limit 2
int ylimit_pin2 = limitSwitchesY.pin2();  //limit 1


long last_time;

Laser laser(SLOT1);

MePort servoPort(PORT_7);
int servopin = servoPort.pin2();
Servo servoPen;

// LEDs turn on when laser is on
MeRGBLed rgbLed(0, 12);


/************** motor movements ******************/
void moveXStepper(int direction) {
  if (direction > 0) {
    stepperX.dWrite1(LOW);
  } else {
    stepperX.dWrite1(HIGH);
  }
  stepperX.dWrite2(HIGH);
  stepperX.dWrite2(LOW);
}

void moveYStepper(int direction) {
  if (direction > 0) {
    stepperY.dWrite1(LOW);
  } else {
    stepperY.dWrite1(HIGH);
  }
  stepperY.dWrite2(HIGH);
  stepperY.dWrite2(LOW);
}


/************** calculate movements ******************/
long stepAuxDelay = 0;
int stepdelay_min = 200;
int stepdelay_max = 1000;
#define SPEED_STEP 1

void doMove() {
  long mDelay = stepdelay_max;
  long temp_delay;
  int speedDiff = -SPEED_STEP;
  int dA, dB, maxD;
  float stepA, stepB, cntA = 0, cntB = 0;
  int d;
  dA = targetXStepperPosition - currentXStepperPosition;
  dB = targetYStepperPosition - currentYStepperPosition;
  maxD = max(abs(dA), abs(dB));
  stepA = (float)abs(dA) / (float)maxD;
  stepB = (float)abs(dB) / (float)maxD;
  //  Serial.print("tarA:");
  //  Serial.print(tarA);
  //  Serial.print(" ,tarB:");
  //  Serial.println(tarB);
  //Serial.printf("move: max:%d da:%d db:%d\n",maxD,dA,dB);
  //  Serial.print(stepA);Serial.print(' ');Serial.println(stepB);
  for (int i = 0; (currentXStepperPosition != targetXStepperPosition) || (currentYStepperPosition != targetYStepperPosition); i++) {  // Robbo1 2015/6/8 Changed - change loop terminate test to test for moving not finished rather than a preset amount of moves
    //Serial.printf("step %d A:%d B;%d tar:%d %d\n",i,posA,posB,tarA,tarB);
    // move A
    if (currentXStepperPosition != targetXStepperPosition) {
      cntA += stepA;
      if (cntA >= 1) {
        d = dA > 0 ? STEPPER_X_FORWARD : STEPPER_X_BACKWARD;
        currentXStepperPosition += (dA > 0 ? 1 : -1);
        moveXStepper(d);
        cntA -= 1;
      }
    }
    // move B
    if (currentYStepperPosition != targetYStepperPosition) {
      cntB += stepB;
      if (cntB >= 1) {
        d = dB > 0 ? STEPPER_Y_FORWARD : STEPPER_Y_BACKWARD;
        currentYStepperPosition += (dB > 0 ? 1 : -1);
        moveYStepper(d);
        cntB -= 1;
      }
    }
    mDelay = constrain(mDelay + speedDiff, stepdelay_min, stepdelay_max);
    temp_delay = mDelay + stepAuxDelay;
    if (millis() - last_time > 400) {
      //      Serial.print("posA:");
      //      Serial.print(posA);
      //      Serial.print(" ,posB:");
      //      Serial.println(posB);
      last_time = millis();
      if (true == process_serial()) {
        return;
      }
    }

    if (temp_delay > stepdelay_max) {
      temp_delay = stepAuxDelay;
      delay(temp_delay / 1000);
      delayMicroseconds(temp_delay % 1000);
    } else {
      delayMicroseconds(temp_delay);
    }
    if ((maxD - i) < ((stepdelay_max - stepdelay_min) / SPEED_STEP)) {
      speedDiff = SPEED_STEP;
    }
  }
  //Serial.printf("finally %d A:%d B;%d\n",maxD,posA,posB);
  currentXStepperPosition = targetXStepperPosition;
  currentYStepperPosition = targetYStepperPosition;
}

/******** mapping xy position to steps ******/
#define STEPS_PER_CIRCLE 3200.0f
#define WIDTH 380
#define HEIGHT 310
#define DIAMETER 11  // the diameter of stepper wheel
//#define STEPS_PER_MM (STEPS_PER_CIRCLE/PI/DIAMETER)
#define STEPS_PER_MM 87.58  // the same as 3d printer
void prepareMove() {
  float dx = targetX - currentX;
  float dy = targetY - currentY;
  float distance = sqrt(dx * dx + dy * dy);
  Serial.print("distance=");
  Serial.println(distance);
  if (distance < 0.001)
    return;
  targetXStepperPosition = targetX * STEPS_PER_MM;
  targetYStepperPosition = targetY * STEPS_PER_MM;
  //Serial.print("tarL:");Serial.print(tarL);Serial.print(' ');Serial.print("tarR:");Serial.println(tarR);
  //Serial.print("curL:");Serial.print(curL);Serial.print(' ');Serial.print("curR:");Serial.println(curR);
  //Serial.printf("tar Pos %ld %ld\r\n",tarA,tarB);
  doMove();
  currentX = targetX;

  currentY = targetY;
}

void goHome() {
  // stop on either endstop touches
  while (digitalRead(ylimit_pin2) == 1 && digitalRead(ylimit_pin1) == 1) {
    moveYStepper(STEPPER_Y_BACKWARD);
    delayMicroseconds(stepdelay_min);
  }
  while (digitalRead(xlimit_pin2) == 1 && digitalRead(xlimit_pin1) == 1) {
    moveXStepper(STEPPER_X_BACKWARD);
    delayMicroseconds(stepdelay_min);
  }
  //  Serial.println("goHome!");
  currentXStepperPosition = 0;
  currentYStepperPosition = 0;
  currentX = 0;
  currentY = 0;
  targetX = 0;
  targetY = 0;
  targetXStepperPosition = 0;
  targetYStepperPosition = 0;
}

void initPosition() {
  currentX = 0;
  currentY = 0;
  currentXStepperPosition = 0;
  currentYStepperPosition = 0;
}


/************** calculate movements ******************/
void parseCordinate(char* cmd) {
  char* tmp;
  char* str;
  str = strtok_r(cmd, " ", &tmp);
  targetX = currentX;
  targetY = currentY;
  while (str != NULL) {
    str = strtok_r(0, " ", &tmp);
    if (str[0] == 'X') {
      targetX = atof(str + 1);
    } else if (str[0] == 'Y') {
      targetY = atof(str + 1);
    } else if (str[0] == 'A') {
      stepAuxDelay = atol(str + 1);
    }
  }
  //  Serial.print("tarX:");
  //  Serial.print(tarX);
  //  Serial.print(", tarY:");
  //  Serial.print(tarY);
  //  Serial.print(", stepAuxDelay:");
  //  Serial.println(stepAuxDelay);
  prepareMove();
}stepAuxDelay

void echoEndStop() {
  Serial.print("M11 ");
  Serial.print(digitalRead(ylimit_pin2));
  Serial.print(" ");
  Serial.print(digitalRead(ylimit_pin1));
  Serial.print(" ");
  Serial.print(digitalRead(xlimit_pin2));
  Serial.print(" ");
  Serial.println(digitalRead(xlimit_pin1));
}

void parseAuxDelay(char* cmd) {
  char* tmp;
  strtok_r(cmd, " ", &tmp);
  stepAuxDelay = atol(tmp);
}


// parseLaserPower function with added light control
void parseLaserPower(char* cmd) {
  char* tmp;
  strtok_r(cmd, " ", &tmp);
  int power = atoi(tmp);

  laser.setPower(power);

  // Turn on lights if the laser is on
  if (laser.isOn()) {
    rgbLed.setColor(0, 255, 0, 0);
    rgbLed.show();
  } else {
    rgbLed.setColor(0, 0, 0, 0);
    rgbLed.show();
  }
}


void parsePen(char* cmd) {
  char* tmp;
  strtok_r(cmd, " ", &tmp);
  int pos = atoi(tmp);
  servoPen.write(pos);
}


void parseMcode(char* cmd) {
  int code;
  code = atoi(cmd);
  switch (code) {
    case 3:
      parseAuxDelay(cmd);
      break;
    case 4:
      parseLaserPower(cmd);
      break;
    case 11:
      echoEndStop();
      break;
  }
}

void parseGcode(char* cmd) {
  int code;
  code = atoi(cmd);
  switch (code) {
    case 0:
    case 1:  // xyz move
      parseCordinate(cmd);
      break;
    case 28:  // home
      stepAuxDelay = 0;
      targetX = 0;
      targetY = 0;
      laser.turnOff();
      goHome();
      break;
  }
}

void parseCmd(char* cmd) {
  if (cmd[0] == 'G') {  // gcode
    parseGcode(cmd + 1);
  } else if (cmd[0] == 'M') {  // mcode
    parseMcode(cmd + 1);
  } else if (cmd[0] == 'P') {
    Serial.print("POS X");
    Serial.print(currentX);
    Serial.print(" Y");
    Serial.println(currentY);
  }
  Serial.println("OK");
}

// local data
void initRobotSetup() {
  int spd = 100 - (85);
  stepdelay_min = spd * 10;
  stepdelay_max = spd * 100;
}




char buf[64];
int8_t bufindex;

boolean process_serial(void) {
  boolean result = false;
  memset(buf, 0, 64);
  bufindex = 0;
  while (Serial.available()) {
    char c = Serial.read();
    buf[bufindex++] = c;
    if (c == '\n') {
      buf[bufindex] = '\0';
      parseCmd(buf);
      result = true;
      memset(buf, 0, 64);
      bufindex = 0;
    }
    if (bufindex >= 64) {
      bufindex = 0;
    }
  }
  return result;
}

/************** arduino ******************/
void setup() {
  pinMode(ylimit_pin1, INPUT_PULLUP);
  pinMode(ylimit_pin2, INPUT_PULLUP);
  pinMode(xlimit_pin1, INPUT_PULLUP);
  pinMode(xlimit_pin2, INPUT_PULLUP);
  Serial.begin(115200);
  initRobotSetup();
  initPosition();
  servoPen.attach(servopin);
  delay(100);
  servoPen.write(0);
  TCCR1A = _BV(WGM10);              // Fast PWM, 8-bit
  TCCR1B = _BV(WGM12) | _BV(CS10);  // No prescaling, Fast PWM

  rgbLed.setpin(44);
  rgbLed.fillPixelsBak(0, 2, 1);

  rgbLed.setColor(0, 0, 0, 0);  // Ensure lights are off initially
  rgbLed.show();
  // Set up the timer to call laser.loop() every 5ms
  // setupTimer();
}

void loop() {
  // Handle incoming serial commands
  if (Serial.available()) {
    char c = Serial.read();
    buf[bufindex++] = c;
    if (c == '\n') {
      buf[bufindex] = '\0';  // Null terminate the string
      parseCmd(buf);         // Parse the command
      memset(buf, 0, 64);    // Clear the buffer
      bufindex = 0;
    }
    if (bufindex >= 64) {
      bufindex = 0;
    }
  }
}
