
// This code has been rewritten for speed by Jason Dorie


// our point structure to make things nice.
struct FloatPoint {
  float x;
  float y;
  float z;
};

struct LongPoint {
  long  x;
  long  y;
  long  z;
};

struct GCodeParams {
  float x, y, z;
  float i, j, k;
  float f;

  byte paramValid;    // X = bit0, Y = bit1, etc...
};


// Stored as thousandths
struct IGCodeParams {
  long  x, y, z;
  long  i, j, k;
  long  f;

  byte paramValid;    // X = bit0, Y = bit1, etc...
};


const byte P_X = 1<<0;
const byte P_Y = 1<<1;
const byte P_Z = 1<<2;
const byte P_I = 1<<3;
const byte P_J = 1<<4;
const byte P_K = 1<<5;
const byte P_F = 1<<6;

LongPoint current_funits; // current units in fixed point
LongPoint target_funits;
LongPoint delta_funits;


LongPoint current_steps;
LongPoint target_steps;
LongPoint delta_steps;

boolean abs_mode = false;   //0 = incremental; 1 = absolute

//default to inches for units
float x_units = X_STEPS_PER_MM;
float y_units = Y_STEPS_PER_MM;
float z_units = Z_STEPS_PER_MM;

long  x_funits;
long  y_funits;
long  z_funits;


//our direction vars
byte x_direction = 1;
byte y_direction = 1;
byte z_direction = 1;

//init our string processing
void init_process_string()
{
  //init our command
  //for (byte i = 0; i < COMMAND_SIZE; i++)
  //  commands[i] = 0;
  serial_count = 0;
}

//our feedrate variables.
float feedrate = 0.0;
float lastRate = 500.0;
long feedrate_micros = 0;


void ParseSetupCommand( char * instruction, byte & index , byte size );
void ParseGCodeInstruction( char * instruction, byte & index , byte size );
void ParseGCodeParams( char * instruction, byte & index, byte size, GCodeParams & gc );
void ParseGCodeParams( char * instruction, byte & index, byte size, IGCodeParams & gc );
void ParseMCodeInstruction( char * instruction, byte & index , byte size );

void ParseIntegerTriple( char * instruction , byte & index , byte size , LongPoint & pt );    // int values labelled XYZ
void ParseFloatTriple( char * instruction , byte & index , byte size , FloatPoint & ptf );     // float values labelled XYZ
long GetInteger( char * instruction, byte & index , byte size );
float GetFloat( char * instruction, byte & index , byte size );
long GetFixedInteger( char * instruction, byte & index , byte size );
long GetFloatAsInteger( char * instruction, byte & index , byte size , long & scale );
void SkipNumber( char * instruction, byte & index , byte size );


void UpdateFUnits(void)
{
  // GCode is parsed into *1000 units, 
  x_funits = (long)(x_units * 256.0 / 1000.0 * 1024.0 + 0.5);
  y_funits = (long)(y_units * 256.0 / 1000.0 * 1024.0 + 0.5);
  z_funits = (long)(z_units * 256.0 / 1000.0 * 1024.0 + 0.5);
}


void process_string(char instruction[], byte size)
{
  //the character / means delete block... used for comments and stuff.
  if (instruction[0] == '/')
  {
    Serial.println("ok");
    return;
  }

  if( size == 1 ) {
    Serial.print("start");
    return;
  }

  // parse the line into whatever we get

  // N# = line number (skip)
  // G# = gcode command
  // M# = motor command

  byte index = 0;
  while( index < size )
  {
    switch( instruction[index] )
    {
      case '$':
        index++;
        ParseSetupCommand( instruction, index, size );
        break;

      case 'N':
      case 'n':
        index++;
        SkipNumber( instruction, index, size ); // skip the line number
        break;

      case 'G':
      case 'g':
        index++;
        ParseGCodeInstruction( instruction, index, size );
        break;

      case 'M':
      case 'm':
        index++;
        ParseMCodeInstruction( instruction, index, size );
        break;

      case 'x':
      case 'X':
      case 'y':
      case 'Y':
      case 'z':
      case 'Z':
        ParseGCodeInstruction( instruction, index, size );
        break;

      case 'h':
      case 'H':
        index++;
        SkipNumber( instruction, index, size ); // skip params we don't understand
        break;

      default:
        index++;
        break;
    }
  }

  Serial.println("ok");
}

void ParseGCodeInstruction( char * instruction, byte & index , byte size )
{
  // G0 = rapid goto
  // G1 = feedrate goto
  // G2 = clockwise arc
  // G3 = counter-clockwise arc
  // G4 = dwell

  // G20 = inch units
  // G20 = mm units
  // G28 = go home
  // G30 = home via intermediate point
  // G90 = use absolute positioning
  // G91 = use relative positioning
  // G92 = set as home

  //FloatPoint fp;
  LongPoint lp;

  long CommandScale;
  long Command = GetFloatAsInteger( instruction, index, size, CommandScale );

  IGCodeParams gc;
  gc.x = gc.y = gc.z = 0.0;

  ParseGCodeParams( instruction, index, size, gc );

  if( Command >= 0 && Command < 4 )
  {
    if( abs_mode )
    {
      if( gc.paramValid & P_X ) {
        lp.x = gc.x;
      }
      else {
        lp.x = current_funits.x;
      }
  
      if( gc.paramValid & P_Y ) {
        lp.y = gc.y;
      }
      else {
        lp.y = current_funits.y;
      }

      if( gc.paramValid & P_Z ) {
        lp.z = gc.z;
      }
      else {
        lp.z = current_funits.z;
      }
    }
    else
    {
        lp.x = current_funits.x + gc.x;
        lp.y = current_funits.y + gc.y;
        lp.z = current_funits.z + gc.z;
    }
  }

  switch( Command )
  {
    case 0:
    case 1:
      set_ftarget(lp.x, lp.y, lp.z);

      //adjust if we have a specific feedrate.
      if(Command == 1)
      {
        //how fast do we move?
        if( gc.paramValid & P_F ) {
          feedrate = gc.f * 0.001;
          lastRate = feedrate;
          feedrate_micros = calculate_feedrate_delay(feedrate);
        }
        else  //nope, no feedrate - use previous
        {
          feedrate = lastRate;
          feedrate_micros = calculate_feedrate_delay(feedrate);
        }
      }
      //use our max for normal moves.
      else
        feedrate_micros = getMaxSpeed();

      dda_move(feedrate_micros, Command == 0);
      break;

    case 2: //Clockwise arc
    case 3: //Counterclockwise arc
      LongPoint cent;

      //how fast do we move?
      if( gc.paramValid & P_F ) {
        feedrate = gc.f * 0.001;
        lastRate = feedrate;
      }
      else {
        feedrate = lastRate;
      }

      // Centre coordinates are always relative
      cent.x = current_funits.x;
      cent.y = current_funits.y;

      if( gc.paramValid & P_I ) cent.x += gc.i;
      if( gc.paramValid & P_J ) cent.y += gc.j;

      float angleA, angleB, angle, radius, length, aX, aY, bX, bY;

      aX = (current_funits.x - cent.x) * 0.001;
      aY = (current_funits.y - cent.y) * 0.001;
      bX = (lp.x - cent.x);
      bY = (lp.y - cent.y);

      if (Command == 2) { // Clockwise
        angleA = atan2(bY, bX);
        angleB = atan2(aY, aX);
      } else { // Counterclockwise
        angleA = atan2(aY, aX);
        angleB = atan2(bY, bX);
      }

      // Make sure angleB is always greater than angleA
      // and if not add 2PI so that it is (this also takes
      // care of the special case of angleA == angleB,
      // ie we want a complete circle)
      if (angleB <= angleA) angleB += 2 * M_PI;
      angle = angleB - angleA;

      radius = sqrt(aX * aX + aY * aY);
      length = radius * angle;

      {
        long cx = to_fsteps( x_funits , cent.x );
        long cy = to_fsteps( y_funits , cent.y );

        set_ftarget(lp.x, lp.y, lp.z);

        feedrate_micros = calculate_feedrate_delay_circle(feedrate , length);
        dda_circle( feedrate_micros, cx, cy, Command == 3 );
      }
      break;

    case 20:
      x_units = X_STEPS_PER_INCH;
      y_units = Y_STEPS_PER_INCH;
      z_units = Z_STEPS_PER_INCH;

      UpdateFUnits();
      calculate_fdeltas();
      break;

    case 21:
      x_units = X_STEPS_PER_MM;
      y_units = Y_STEPS_PER_MM;
      z_units = Z_STEPS_PER_MM;

      UpdateFUnits();
      calculate_fdeltas();
      break;

    case 28:
      set_ftarget(0, 0, 0);
      dda_move(getMaxSpeed(), 1);
      break;

    case 90:
      abs_mode = true;
      Serial.println("abs mode");
      break;

    case 901:
      // CommandScale == 10, actual value is 90.1, absolute arc positions
      Serial.println("abs arcs");
      break;

    case 91:
      abs_mode = false;
      Serial.println("rel mode");
      break;

    case 911:
      // CommandScale == 10, actual value is 91.1, relative arc positions
      Serial.println("rel arcs");
      break;

    case 92:
      set_fposition(0, 0, 0);
      break;

    default:
      Serial.print("huh? G");
      Serial.println(Command, DEC);
      break;
  }
}


void ParseMCodeInstruction( char * instruction, byte & index , byte size )
{
  int Command = GetInteger( instruction, index, size );
  Serial.print( "M" );
  Serial.println(Command, DEC);
}



void ParseSetupCommand( char * instruction, byte & index , byte size )
{
  // $ commands:
  // $1 X# Y# Z#  = step pin
  // $2 X# Y# Z#  = dir pin
  // $3 X# Y# Z#  = min pin (limit) - may not have a digit
  // $4 X# Y# Z#  = max pin (limit)
  // $5 Z#        = enable servo
  // $6 X# Y# Z#  = steps per mm
  // $7 X# Y# Z#  = fast feedrate for axis
  // $8 S#        = invert limit switches

  if( index == size ) return;

  char command = instruction[index++];
  GCodeParams gc;
  ParseGCodeParams( instruction, index, size, gc );

  switch( command )
  {
    case '1': // step pin per axis
      if( gc.paramValid & P_X ) {
        X_STEP_PIN = (int)gc.x;
        pinMode(X_STEP_PIN, OUTPUT);
        digitalWrite(X_STEP_PIN, LOW);

        XSTEP_PORT = portOutputRegister( digitalPinToPort(X_STEP_PIN) );
        XSTEP_MASK = digitalPinToBitMask(X_STEP_PIN);
      }

      if( gc.paramValid & P_Y ) {
        Y_STEP_PIN = (int)gc.y;
        pinMode(Y_STEP_PIN, OUTPUT);
        digitalWrite(Y_STEP_PIN, LOW);

        YSTEP_PORT = portOutputRegister( digitalPinToPort(Y_STEP_PIN) );
        YSTEP_MASK = digitalPinToBitMask(Y_STEP_PIN);
      }

      if( (gc.paramValid & P_Z) && gc.z != 0.0) {
        int TEMP_PIN = (int)gc.z;

        if (Z_STEP_PIN != TEMP_PIN) {
          Z_STEP_PIN = TEMP_PIN;
          if (Z_ENABLE_SERVO == 1) {
            servo.attach(Z_STEP_PIN);
          } else {
            pinMode(Z_STEP_PIN, OUTPUT);
            digitalWrite(Z_STEP_PIN, LOW);
          }
        }
      }
      break;

    case '2': // dir pin per axis
      if( gc.paramValid & P_X ) {
        X_DIR_PIN = (byte)gc.x;
        pinMode(X_DIR_PIN, OUTPUT);
        digitalWrite(X_DIR_PIN, LOW);

        XDIR_PORT = portOutputRegister( digitalPinToPort(X_DIR_PIN) );
        XDIR_MASK = digitalPinToBitMask(X_DIR_PIN);
      }

      if( gc.paramValid & P_Y ) {
        Y_DIR_PIN = (byte)gc.y;
        pinMode(Y_DIR_PIN, OUTPUT);
        digitalWrite(Y_DIR_PIN, LOW);

        YDIR_PORT = portOutputRegister( digitalPinToPort(Y_DIR_PIN) );
        YDIR_MASK = digitalPinToBitMask(Y_DIR_PIN);
      }

      if( (gc.paramValid & P_Z) && gc.z != 0.0 ) {
        Z_DIR_PIN = (byte)gc.z;
        pinMode(Z_DIR_PIN, OUTPUT);
        digitalWrite(Z_DIR_PIN, LOW);
      }
      break;

    case '3': // min pin per axis
      if( gc.paramValid & P_X ) {
        X_MIN_PIN = (byte)gc.x;
        pinMode(X_MIN_PIN, INPUT_PULLUP);
      }

      if( gc.paramValid & P_Y ) {
        Y_MIN_PIN = (byte)gc.y;
        pinMode(Y_MIN_PIN, INPUT_PULLUP);
      }

      if( (gc.paramValid & P_Z) && gc.z != 0.0 ) {
        Z_MIN_PIN = (byte)gc.z;
        pinMode(Z_MIN_PIN, INPUT_PULLUP);
      }
      break;

    case '4': // max pin per axis
      if( gc.paramValid & P_X ) {
        X_MAX_PIN = (byte)gc.x;
        pinMode(X_MAX_PIN, INPUT_PULLUP);
      }

      if( gc.paramValid & P_Y ) {
        Y_MAX_PIN = (byte)gc.y;
        pinMode(Y_MAX_PIN, INPUT_PULLUP);
      }

      if( (gc.paramValid & P_Z) && gc.z != 0.0 ) {
        Z_MAX_PIN = (byte)gc.z;
        pinMode(Z_MAX_PIN, INPUT_PULLUP);
      }
      break;

    case '5': // servo enable
      if( gc.paramValid & P_Z ) {
        Z_ENABLE_SERVO = (byte)gc.z;
      }
      break;

    case '6': // steps per mm per axis
      if( gc.paramValid & P_X ) {
        X_STEPS_PER_MM = gc.x * 0.5;
        x_units = X_STEPS_PER_MM;
        Serial.println(x_units);
      }

      if( gc.paramValid & P_Y ) {
        Y_STEPS_PER_MM = gc.y * 0.5;
        y_units = Y_STEPS_PER_MM;
        Serial.println(y_units);
      }

      if( (gc.paramValid & P_Z) && gc.z != 0.0 ) {
        Z_STEPS_PER_MM = gc.z;
        z_units = Z_STEPS_PER_MM;
        Serial.println(z_units);
      }

      UpdateFUnits();
      break;

    case '7': // fast feedrate per axis
      if( gc.paramValid & P_X ) {
        FAST_XY_FEEDRATE = gc.x;
      }

      if( gc.paramValid & P_Y ) {
        FAST_XY_FEEDRATE = gc.y;
      }

      if( (gc.paramValid & P_Z) && gc.z != 0.0 ) {
        FAST_Z_FEEDRATE = gc.z;
      }
      break;
  }
}


void ParseIntegerTriple( char * instruction , byte & index , byte size , LongPoint & pt )
{
  pt.x = pt.y = pt.z = 0;
  while( index < size ) {
    switch( instruction[index] )
    {
      case 'X':
      case 'x':
        index++;
        pt.x = GetInteger( instruction, index, size );
        break;

      case 'Y':
      case 'y':
        index++;
        pt.y = GetInteger( instruction, index, size );
        break;

      case 'Z':
      case 'z':
        index++;
        pt.z = GetInteger( instruction, index, size );
        break;

      case ' ':
      case '\t':
        index++;
        break;

    default:
      return;
    }
  }
}

void ParseFloatTriple( char * instruction , byte & index , byte size , FloatPoint & ptf )
{
  ptf.x = ptf.y = ptf.z = 0.0;

  instruction[size] = 0;
  //Serial.println( instruction );

  while( index < size )
  {
    switch( instruction[index] )
    {
      case 'X':
      case 'x':
        index++;
        ptf.x = GetFloat( instruction, index, size );
        break;

      case 'Y':
      case 'y':
        index++;
        ptf.y = GetFloat( instruction, index, size );
        break;

      case 'Z':
      case 'z':
        index++;
        ptf.z = GetFloat( instruction, index, size );
        break;

      case ' ':
      case '\t':
        index++;
        break;

    default:
      return;
    }
  }
}


void ParseGCodeParams( char * instruction, byte & index, byte size, GCodeParams & gc )
{
  gc.paramValid = 0;

  while( index < size )
  {
    switch( instruction[index] )
    {
      case 'X':
      case 'x':
        index++;
        gc.x = GetFloat( instruction, index, size );
        gc.paramValid |= (1<<0);
        //Serial.print( "  X: "); Serial.print( gc.x );
        break;

      case 'Y':
      case 'y':
        index++;
        gc.y = GetFloat( instruction, index, size );
        gc.paramValid |= (1<<1);
        //Serial.print( "  Y: "); Serial.print( gc.y );
        break;

      case 'Z':
      case 'z':
        index++;
        gc.z = GetFloat( instruction, index, size );
        gc.paramValid |= (1<<2);
        //Serial.print( "  Z: "); Serial.print( gc.z );
        break;

      /*
      case 'I':
      case 'i':
        index++;
        gc.i = GetFloat( instruction, index, size );
        gc.paramValid |= (1<<3);
        //Serial.print( "  I: "); Serial.print( gc.i );
        break;

      case 'J':
      case 'j':
        index++;
        gc.j = GetFloat( instruction, index, size );
        gc.paramValid |= (1<<4);
        //Serial.print( "  J: "); Serial.print( gc.j );
        break;

      case 'K':
      case 'k':
        index++;
        gc.k = GetFloat( instruction, index, size );
        gc.paramValid |= (1<<5);
        //Serial.print( "  K: "); Serial.print( gc.k );
        break;

      case 'F':
      case 'f':
        index++;
        gc.f = GetFloat( instruction, index, size );
        gc.paramValid |= (1<<6);
        //Serial.print( "  F: "); Serial.print( gc.f );
        break;
      */

      case ' ':
      case '\t':
        index++;
        break;

    default:
      //Serial.print(" ??: " );
      //Serial.println( (int)instruction[index] );
      return;
    }
  }
  //Serial.println("");
}


void ParseGCodeParams( char * instruction, byte & index, byte size, IGCodeParams & gc )
{
  gc.paramValid = 0;

  while( index < size )
  {
    switch( instruction[index] )
    {
      case 'X':
      case 'x':
        index++;
        gc.x = GetFixedInteger( instruction, index, size );
        gc.paramValid |= (1<<0);
        //Serial.print( "  X: "); Serial.print( gc.x );
        break;

      case 'Y':
      case 'y':
        index++;
        gc.y = GetFixedInteger( instruction, index, size );
        gc.paramValid |= (1<<1);
        //Serial.print( "  Y: "); Serial.print( gc.y );
        break;

      case 'Z':
      case 'z':
        index++;
        gc.z = GetFixedInteger( instruction, index, size );
        gc.paramValid |= (1<<2);
        //Serial.print( "  Z: "); Serial.print( gc.z );
        break;

      case 'I':
      case 'i':
        index++;
        gc.i = GetFixedInteger( instruction, index, size );
        gc.paramValid |= (1<<3);
        //Serial.print( "  I: "); Serial.print( gc.i );
        break;

      case 'J':
      case 'j':
        index++;
        gc.j = GetFixedInteger( instruction, index, size );
        gc.paramValid |= (1<<4);
        //Serial.print( "  J: "); Serial.print( gc.j );
        break;

      case 'K':
      case 'k':
        index++;
        gc.k = GetFixedInteger( instruction, index, size );
        gc.paramValid |= (1<<5);
        //Serial.print( "  K: "); Serial.print( gc.k );
        break;

      case 'F':
      case 'f':
        index++;
        gc.f = GetFixedInteger( instruction, index, size );
        gc.paramValid |= (1<<6);
        //Serial.print( "  F: "); Serial.print( gc.f );
        break;

      case ' ':
      case '\t':
        index++;
        break;

    default:
      //Serial.print(" ??: " );
      //Serial.println( (int)instruction[index] );
      return;
    }
  }
  //Serial.println("");
}



long GetInteger( char * instruction, byte & index , byte size )
{
  bool isNeg = false;
  long res = 0;
  if( instruction[index] == '-' ) {
    isNeg = true;
    index++;
  }

  while( index < size && (instruction[index] >= '0' && instruction[index] <= '9' )) {
    res *= 10;
    res += instruction[index++] - '0';
  }

  // if there was a decimal, skip it and any trailing digits
  while( index < size )
  {
    char c = instruction[index];
    if( c == '.' || (c >= '0' && c <= '9' )) {
        index++;
    }
    else break;
  }

  if( isNeg ) res = -res;
  return res;
}

void SkipNumber( char * instruction, byte & index , byte size )
{
  while( index < size ) {
    char c = instruction[index];
    if( c == '-' || c == '.' || (c>='0' && c <= '9') ) {
      index++;
    }
    else
      return;
  }
}


long GetFloatAsInteger( char * instruction, byte & index , byte size , long & scale )
{
  bool isNeg = false, foundDec = false;
  long res = 0;
  scale = 1;

  if( instruction[index] == '-' ) {
    isNeg = true;
    index++;
  }

  while( index < size )
  {
    char c = instruction[index];
    if( c >= '0' && c <= '9' )
    {
      res *= 10;
      res += (c - '0');
      if( foundDec ) scale *= 10;
      index++;
    }
    else if( c == '.' )
    {
      foundDec = true;
      index++;
    }
    else
      break;
  }
  if( isNeg ) res = -res;
  return res;
}

float GetFloat( char * instruction, byte & index , byte size )
{
  long scale;
  long res = GetFloatAsInteger(instruction, index, size, scale );
  return (float)res / (float)scale;
}


// Returns everything scaled up by 1000
long GetFixedInteger( char * instruction, byte & index , byte size )
{
  bool isNeg = false, foundDec = false;
  long res = 0;
  byte scale = 0;

  if( instruction[index] == '-' ) {
    isNeg = true;
    index++;
  }

  while( index < size )
  {
    char c = instruction[index];
    if( c >= '0' && c <= '9' )
    {
      if( scale < 3 ) {
        res *= 10;
        res += (c - '0');
        if( foundDec ) scale++;
      }
      index++;
    }
    else if( c == '.' )
    {
      foundDec = true;
      index++;
    }
    else
      break;
  }

  while( scale < 3 ) {
    res *= (byte)10;
    scale++;
  }

  if( isNeg ) res = -res;
  return res;
}



//look for the number that appears after the char key and return it
double search_string(char key, char instruction[], int string_size)
{
  char temp[10] = "";

  for (byte i = 0; i < string_size; i++)
  {
    if (instruction[i] == key)
    {
      i++;
      int k = 0;
      while (i < string_size && k < 10)
      {
        if (instruction[i] == 0 || instruction[i] == ' ')
          break;

        temp[k] = instruction[i];
        i++;
        k++;
      }
      return strtod(temp, NULL);
    }
  }

  return 0;
}

//look for the command if it exists.
bool has_command(char key, char instruction[], int string_size)
{
  for (byte i = 0; i < string_size; i++)
  {
    if (instruction[i] == key)
      return true;
  }

  return false;
}
