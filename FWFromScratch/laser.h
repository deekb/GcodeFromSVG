#ifndef LASER_H
#define LASER_H

#include <Arduino.h>

class Laser {
  private:
    int pwmPin;
    int driverH1Pin;
    int driverH2Pin;
    
  public:
    // Constructor
    Laser(int pwmPin, int driverH1Pin, int driverH2Pin);

    // Method to initialize the pins
    void begin();

    // Method to set the laser power (PWM)
    void setPower(int16_t power);
};

#endif
