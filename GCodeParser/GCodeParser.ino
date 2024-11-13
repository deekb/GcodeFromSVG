
// This code has been rewritten for speed by Jason Dorie

#include "Makeblock.h"
#include <Servo.h>

// define the parameters of our machine.
float X_STEPS_PER_INCH = 48;
float X_STEPS_PER_MM = 40;
int X_MOTOR_STEPS   = 100;

float Y_STEPS_PER_INCH = 48;
float Y_STEPS_PER_MM  = 40;
int Y_MOTOR_STEPS   = 100;

float Z_STEPS_PER_INCH = 48;
float Z_STEPS_PER_MM   = 40;
int Z_MOTOR_STEPS    = 100;

//our maximum feedrates
int FAST_XY_FEEDRATE = 5000;
int FAST_Z_FEEDRATE = 5000;

// Set to one if sensor outputs inverting (ie: 1 means open, 0 means closed)
// RepRap opto endstops are *not* inverting.
int SENSORS_INVERTING = 1;

MeDCMotor laser(M2);

// How many temperature samples to take.  each sample takes about 100 usecs.


/****************************************************************************************
  digital i/o pin assignment

  this uses the undocumented feature of Arduino - pins 14-19 correspond to analog 0-5
****************************************************************************************/

int X_STEP_PIN = 10;
int X_DIR_PIN = 11;
int X_MIN_PIN = 17;
int X_MAX_PIN = 16;

int Y_STEP_PIN = 9;
int Y_DIR_PIN = 3;
int Y_MIN_PIN = 13;
int Y_MAX_PIN = 12;

volatile uint8_t *XSTEP_PORT = 0;
volatile uint8_t *XDIR_PORT = 0;
volatile uint8_t *XMIN_PORT = 0;
volatile uint8_t *XMAX_PORT = 0;
volatile uint8_t *YSTEP_PORT = 0;
volatile uint8_t *YDIR_PORT = 0;
volatile uint8_t *YMIN_PORT = 0;
volatile uint8_t *YMAX_PORT = 0;

uint8_t XSTEP_MASK = 0;
uint8_t YSTEP_MASK = 0;
uint8_t XDIR_MASK = 0;
uint8_t YDIR_MASK = 0;
uint8_t XMIN_MASK = 0;
uint8_t YMIN_MASK = 0;
uint8_t XMAX_MASK = 0;
uint8_t YMAX_MASK = 0;

int Z_STEP_PIN = 15;
int Z_DIR_PIN = -1;
int Z_MIN_PIN = -1;
int Z_MAX_PIN = -1;
int Z_ENABLE_SERVO = 0;
int Z_ENABLE_LASER = 1;
#define COMMAND_SIZE 128

char commands[COMMAND_SIZE];
byte serial_count;
int no_data = 0;

Servo servo;

int currentPosServo = 90;
int targetPosServo = 90;
bool comment = false;
void setup()
{
  //Do startup stuff here
  Serial.begin(115200);
  if (Z_ENABLE_SERVO == 1) {
    servo.attach(Z_STEP_PIN);
  }
  //other initialization.
  init_process_string();
  init_steppers();
  process_string("G90", 3); //Absolute Position
  Serial.println("start");

  laser.run(0);
}

void loop()
{
  char c;
  //read in characters if we got them.
  if (Serial.available() > 0)
  {
    c = Serial.read();
    no_data = 0;
    //newlines are ends of commands.
    if (c != '\n')
    {
      if (c == 0x18) {
        Serial.println("Grbl 1.0");
      } else {
        if (c == '(') {
          comment = true;
        }
        // If we're not in comment mode, add it to our array.
        if (!comment)
        {
          commands[serial_count] = c;
          serial_count++;
        }
        if (c == ')') {
          comment = false; // End of comment - start listening again
        }
      }
    }
    else if(serial_count) // got a command?
    {
      //process our command!
      process_string(commands, serial_count);

      //clear command.
      init_process_string();
    }
  }
  else
  {
    no_data++;
    delayMicroseconds(50);

    //if theres a pause or we got a real command, do it
    if( serial_count && (c == '\n' || no_data > 100) )
    {
      //process our command!
      process_string(commands, serial_count);

      //clear command.
      init_process_string();
    }

    //no data?  turn off steppers
    if (no_data > 2000) {
      //disable_steppers();
      //laser.run(0);
    }
  }
}
