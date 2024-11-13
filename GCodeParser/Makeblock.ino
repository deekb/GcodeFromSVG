#include "Makeblock.h"
#include "wiring_private.h"
#include "pins_arduino.h"
#define MeBaseBoard


#if defined(__AVR_ATmega32U4__) //MeBaseBoard use ATmega32U4 as MCU

MePort_Sig mePort[11] = {{NC, NC}, {11, A8}, {13, A11}, {A10, A9}, {1, 0},
    {MISO, SCK}, {A0, A1}, {A2, A3}, {A4, A5}, {6, 7}, {5, 4}
};
#else // else ATmega328
MePort_Sig mePort[11] = {{NC, NC}, {11, 10}, {3, 9}, {12, 13}, {8, 2},
    {NC, NC}, {A2, A3}, {A6, A1}, {A7, A0}, {6, 7}, {5, 4}
};

#endif

union
{
    byte b[4];
    float fVal;
    long lVal;
} u;

/*        Port       */
MePort::MePort()
{
    s1 = mePort[0].s1;
    s2 = mePort[0].s2;
    _port = 0;
}
MePort::MePort(uint8_t port)
{
    s1 = mePort[port].s1;
    s2 = mePort[port].s2;
    _port = port;
}
uint8_t MePort::getPort()
{
    return _port;
}
uint8_t MePort::getSlot()
{
    return _slot;
}
bool MePort::dRead1()
{
    bool val;
    pinMode(s1, INPUT);
    val = digitalRead(s1);
    return val;
}

bool MePort::dRead2()
{
    bool val;
    pinMode(s2, INPUT);
    val = digitalRead(s2);
    return val;
}

void MePort::dWrite1(bool value)
{
    pinMode(s1, OUTPUT);
    digitalWrite(s1, value);
}

void MePort::dWrite2(bool value)
{
    pinMode(s2, OUTPUT);
    digitalWrite(s2, value);
}

int MePort::aRead1()
{
    int val;
    val = analogRead(s1);
    return val;
}

int MePort::aRead2()
{
    int val;
    val = analogRead(s2);
    return val;
}

void MePort::aWrite1(int value)
{
    analogWrite(s1, value);
}

void MePort::aWrite2(int value)
{
    analogWrite(s2, value);
}
uint8_t MePort::pin1()
{
    return s1;
}
uint8_t MePort::pin2()
{
    return s2;
}
void MePort::reset(uint8_t port)
{
    s1 = mePort[port].s1;
    s2 = mePort[port].s2;
    _port = port;
}
void MePort::reset(uint8_t port, uint8_t slot)
{
    s1 = mePort[port].s1;
    s2 = mePort[port].s2;
    _port = port;
    _slot = slot;
}
/*             Wire               */
MeWire::MeWire(uint8_t address): MePort()
{
    _slaveAddress = address + 1;
}
MeWire::MeWire(uint8_t port, uint8_t address): MePort(port)
{
    _slaveAddress = address + 1;
}
void MeWire::begin()
{
    delay(1000);
    Wire.begin();
    write(BEGIN_FLAG, 0x01);
}
bool MeWire::isRunning()
{
    return read(BEGIN_STATE);
}
void MeWire::setI2CBaseAddress(uint8_t baseAddress)
{
    byte w[2] = {0};
    byte r[4] = {0};
    w[0] = 0x21;
    w[1] = baseAddress;
    request(w, r, 2, 4);
}

byte MeWire::read(byte dataAddress)
{
    byte *b = {0};
    read(dataAddress, b, 1);
    return b[0];
}

void MeWire::read(byte dataAddress, uint8_t *buf, int len)
{
    byte rxByte;
    Wire.beginTransmission(_slaveAddress); // transmit to device
    Wire.write(dataAddress); // sends one byte
    Wire.endTransmission(); // stop transmitting
    delayMicroseconds(1);
    Wire.requestFrom(_slaveAddress, len); // request 6 bytes from slave device
    int index = 0;
    while(Wire.available()) // slave may send less than requested
    {
        rxByte = Wire.read(); // receive a byte as character
        buf[index] = rxByte;
        index++;
    }
}

void MeWire::write(byte dataAddress, byte data)
{
    Wire.beginTransmission(_slaveAddress); // transmit to device
    Wire.write(dataAddress); // sends one byte
    Wire.endTransmission(); // stop transmitting

    Wire.beginTransmission(_slaveAddress); // transmit to device
    Wire.write(data); // sends one byte
    Wire.endTransmission(); // stop transmitting
}
void MeWire::request(byte *writeData, byte *readData, int wlen, int rlen)
{

    uint8_t rxByte;
    uint8_t index = 0;

    Wire.beginTransmission(_slaveAddress); // transmit to device

    Wire.write(writeData, wlen);

    Wire.endTransmission();
    delayMicroseconds(2);
    Wire.requestFrom(_slaveAddress, rlen); // request 6 bytes from slave device
    delayMicroseconds(2);
    while(Wire.available()) // slave may send less than requested
    {
        rxByte = Wire.read(); // receive a byte as character

        readData[index] = rxByte;
        index++;
    }
}


/*             Serial                  */
MeSerial::MeSerial(): MePort(), SoftwareSerial(NC, NC)
{
    _hard = true;
    _scratch = true;
    _polling = false;
}
MeSerial::MeSerial(uint8_t port): MePort(port), SoftwareSerial(mePort[port].s2, mePort[port].s1)
{
    _scratch = false;
    _hard = false;
    _polling = false;
#if defined(__AVR_ATmega32U4__)
    _polling = getPort() > PORT_5;
    _hard = getPort() == PORT_4;
#else
    _hard = getPort() == PORT_5;
#endif
}
void MeSerial::setHardware(bool mode)
{
    _hard = mode;
}
void MeSerial::begin(long baudrate)
{
    _bitPeriod = 1000000 / baudrate;
    if(_hard)
    {
#if defined(__AVR_ATmega32U4__)
        _scratch ? Serial.begin(baudrate) : Serial1.begin(baudrate);
#else
        Serial.begin(baudrate);
#endif
    }
    else
    {
        SoftwareSerial::begin(baudrate);
    }
}

void MeSerial::end()
{
    if(_hard)
    {
#if defined(__AVR_ATmega32U4__)
        Serial1.end();
#else
        Serial.end();
#endif
    }
    else
    {
        SoftwareSerial::end();
    }
}

size_t MeSerial::write(uint8_t byte)
{
    if(_isServoBusy == true)return -1;
    if(_hard)
    {
#if defined(__AVR_ATmega32U4__)
        return (_scratch ? Serial.write(byte) : Serial1.write(byte));
#else
        return Serial.write(byte);
#endif
    }
    else return SoftwareSerial::write(byte);
}
int MeSerial::read()
{
    if(_isServoBusy == true)return -1;

    if(_polling)
    {
        int temp = _byte;
        _byte = -1;
        return temp > -1 ? temp : poll();
    }
    if(_hard)
    {
#if defined(__AVR_ATmega32U4__)
        return (_scratch ? Serial.read() : Serial1.read());
#else
        return Serial.read();
#endif
    }
    else return SoftwareSerial::read();
}
int MeSerial::available()
{
    if(_polling)
    {
        _byte = poll();
        return _byte > -1 ? 1 : 0;
    }
    if(_hard)
    {
#if defined(__AVR_ATmega32U4__)
        return (_scratch ? Serial.available() : Serial1.available());
#else
        return Serial.available();
#endif
    }
    else return SoftwareSerial::available();
}
bool MeSerial::listen()
{
    if(_hard)
        return true;
    else return SoftwareSerial::listen();
}
bool MeSerial::isListening()
{
    if(_hard)
        return true;
    else return SoftwareSerial::isListening();
}

int MeSerial::poll()
{
    int val = 0;
    int bitDelay = _bitPeriod - clockCyclesToMicroseconds(50);
    if (digitalRead(s2) == LOW)
    {
        for (int offset = 0; offset < 8; offset++)
        {
            delayMicroseconds(bitDelay);
            val |= digitalRead(s2) << offset;
        }
        delayMicroseconds(bitDelay);
        return val & 0xff;
    }
    return -1;
}

/*             LineFinder              */
MeLineFollower::MeLineFollower(): MePort(0)
{

}
MeLineFollower::MeLineFollower(uint8_t port): MePort(port)
{

}
uint8_t MeLineFollower::readSensors()
{
    uint8_t state = S1_IN_S2_IN;
    bool s1State = MePort::dRead1();
    bool s2State = MePort::dRead2();
    state = ((1 & s1State) << 1) | s2State;
    return state;
}
bool MeLineFollower::readSensor1()
{
    return MePort::dRead1();
}
bool MeLineFollower::readSensor2()
{
    return MePort::dRead2();
}
/*             LimitSwitch              */
MeLimitSwitch::MeLimitSwitch(): MePort(0)
{
}
MeLimitSwitch::MeLimitSwitch(uint8_t port): MePort(port)
{
    _device = SLOT1;
    pinMode(s2, INPUT_PULLUP);
}
MeLimitSwitch::MeLimitSwitch(uint8_t port, uint8_t slot): MePort(port)
{
    reset(port, slot);
    if(getSlot() == SLOT1)
    {
        pinMode(s1, INPUT_PULLUP);
    }
    else
    {
        pinMode(s2, INPUT_PULLUP);
    }
}
bool MeLimitSwitch::touched()
{
    // if(getSlot()==SLOT2){
    // pinMode(s1,INPUT_PULLUP);
    // }else{
    // pinMode(s2,INPUT_PULLUP);
    // }
    return !(getSlot() == SLOT1 ? digitalRead(s1) : digitalRead(s2));
}

/*             MotorDriver              */
MeDCMotor::MeDCMotor(): MePort(0)
{

}
MeDCMotor::MeDCMotor(uint8_t port): MePort(port)
{
    //The PWM frequency is 976 Hz
#if defined(__AVR_ATmega32U4__) //MeBaseBoard use ATmega32U4 as MCU

    TCCR1A =  _BV(WGM10);
    TCCR1B = _BV(CS11) | _BV(CS10) | _BV(WGM12);

    TCCR3A = _BV(WGM30);
    TCCR3B = _BV(CS31) | _BV(CS30) | _BV(WGM32);

    TCCR4B = _BV(CS42) | _BV(CS41) | _BV(CS40);
    TCCR4D = 0;

#else if defined(__AVR_ATmega328__) // else ATmega328

    TCCR1A = _BV(WGM10);
    TCCR1B = _BV(CS11) | _BV(CS10) | _BV(WGM12);

    TCCR2A = _BV(WGM21) | _BV(WGM20);
    TCCR2B = _BV(CS22);

#endif
}
void MeDCMotor::run(int speed)
{
    speed = speed > 255 ? 255 : speed;
    speed = speed < -255 ? -255 : speed;

    if(speed >= 0)
    {
        MePort::dWrite2(HIGH);
        MePort::aWrite1(speed);
    }
    else
    {
        MePort::dWrite2(LOW);
        MePort::aWrite1(-speed);
    }
}
void MeDCMotor::stop()
{
    MeDCMotor::run(0);
}

