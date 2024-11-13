#include "laser.h"

/**
 * @brief Constructs the Laser object and ensures the laser is turned off initially.
 *
 * This constructor initializes the laser motor driver at the given port and calls
 * `turnOff()` to ensure the laser is off when the object is created.
 *
 * @param laserPort The motor slot the laser is connected to (SLOT1 or SLOT2).
 */
Laser::Laser(int laserPort) : laser(laserPort), currentPower(0) {
    turnOff();  // Ensures laser is off when constructed
}

/**
 * @brief Turns off the laser.
 *
 * Calls `setPower()` with a value of 0 to turn the laser off.
 */
void Laser::turnOff() {
    setPower(0);
}

/**
 * @brief Sets the power of the laser.
 *
 * This function scales the input power from a range of 0-100 to an output range of
 * 0-255 using integer arithmetic, which avoids the use of floating-point operations.
 * The power value is constrained within the range of 0-100. Integer arithmetic is used
 * for performance reasons, particularly because the ATmega2560 microcontroller used in
 * the Me Auriga board lacks a dedicated Floating Point Unit (FPU). Floating-point calculations
 * would be slower as they are handled via software. By using integer arithmetic, the
 * calculation (power * 255) / 100 is efficient, as multiplication and division with integers
 * are relatively fast on this microcontroller. The function then sets the motor PWM of the laser
 * accordingly and inverts the PWM output to be compatible with the Orion board, using the M+ motor output.
 *
 * @param power The desired power level of the laser, in the range 0-100.
 */
void Laser::setPower(int power) {
    power = constrain(power, 0, 100);
    laser.setMotorPwm(-(power * 255) / 100);  // Invert the power to drive M+ instead of M-

    currentPower = power;
}

/**
 * @brief Checks if the laser is currently on.
 *
 * @return True if the laser is on, false otherwise.
 */
bool Laser::isOn() const {
    return currentPower != 0;
}

/**
 * @brief Gets the current power level of the laser.
 *
 * @return The current power level (0-100).
 */
int Laser::getPower() const {
    return currentPower;
}
