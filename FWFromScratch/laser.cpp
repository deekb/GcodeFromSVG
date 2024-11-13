#include "laser.h"

// Constructor definition
Laser::Laser(int pwmPin, int driverH1Pin, int driverH2Pin) {
  this->pwmPin = pwmPin;
  this->driverH1Pin = driverH1Pin;
  this->driverH2Pin = driverH2Pin;
}

// Method to initialize the pins
void Laser::begin() {
  pinMode(driverH1Pin, OUTPUT);
  pinMode(driverH2Pin, OUTPUT);
  pinMode(pwmPin, OUTPUT);
}

// Method to set the laser power (PWM)
void Laser::setPower(int16_t power) {
  power = constrain(power, 0, 255);
  digitalWrite(driverH1Pin, HIGH);
  delayMicroseconds(5);
  digitalWrite(driverH2Pin, LOW);
  analogWrite(pwmPin, abs(power));
}
