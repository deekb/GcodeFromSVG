#ifndef LASER_H
#define LASER_H

#include <MeEncoderOnBoard.h>
#include <Arduino.h>

class Laser {
public:
    Laser(int laserPort);
    void turnOn();
    void turnOff();
    void setPower(int power);
    bool isOn() const;
    int getPower() const;

private:
    MeEncoderOnBoard laser;
    int currentPower;
};

#endif
