
// This code has been rewritten for speed by Jason Dorie

//init our variables
long max_delta;
long x_counter;
long y_counter;
long z_counter;
bool x_can_step;
bool y_can_step;
bool z_can_step;
int milli_delay;

unsigned long STEP = 0;


void init_steppers()
{
	//init our points.
  current_funits.x = 0;
  current_funits.y = 0;
  current_funits.z = 0;
  target_funits.x = 0;
  target_funits.y = 0;
  target_funits.z = 0;


	pinMode(X_STEP_PIN, OUTPUT);
	pinMode(X_DIR_PIN, OUTPUT);
	pinMode(X_MIN_PIN, INPUT_PULLUP);
	pinMode(X_MAX_PIN, INPUT_PULLUP);
	
	pinMode(Y_STEP_PIN, OUTPUT);
	pinMode(Y_DIR_PIN, OUTPUT);
	pinMode(Y_MIN_PIN, INPUT_PULLUP);
	pinMode(Y_MAX_PIN, INPUT_PULLUP);

  // cache all of these mappings so we can bypass DigitalWrite and DigitalRead for speed,
  // but still keep multi-board compatibility

  XSTEP_PORT = portOutputRegister( digitalPinToPort(X_STEP_PIN) );
  XSTEP_MASK = digitalPinToBitMask(X_STEP_PIN);
  YSTEP_PORT = portOutputRegister( digitalPinToPort(Y_STEP_PIN) );
  YSTEP_MASK = digitalPinToBitMask(Y_STEP_PIN);

  XDIR_PORT = portOutputRegister( digitalPinToPort(X_DIR_PIN) );
  XDIR_MASK = digitalPinToBitMask(X_DIR_PIN);
  YDIR_PORT = portOutputRegister( digitalPinToPort(Y_DIR_PIN) );
  YDIR_MASK = digitalPinToBitMask(Y_DIR_PIN);

  XMIN_PORT = portInputRegister( digitalPinToPort(X_MIN_PIN) );
  XMIN_MASK = digitalPinToBitMask(X_MIN_PIN);
  XMAX_PORT = portInputRegister( digitalPinToPort(X_MAX_PIN) );
  XMAX_MASK = digitalPinToBitMask(X_MAX_PIN);

  YMIN_PORT = portInputRegister( digitalPinToPort(Y_MIN_PIN) );
  YMIN_MASK = digitalPinToBitMask(Y_MIN_PIN);
  YMAX_PORT = portInputRegister( digitalPinToPort(Y_MAX_PIN) );
  YMAX_MASK = digitalPinToBitMask(Y_MAX_PIN);

	pinMode(Z_STEP_PIN, OUTPUT);
	pinMode(Z_DIR_PIN, OUTPUT);
	pinMode(Z_MIN_PIN, INPUT_PULLUP);
	pinMode(Z_MAX_PIN, INPUT_PULLUP);
	
	//figure our stuff.
  calculate_fdeltas();
}

bool laserOn = false;

void set_laser_power(void)
{
  int lz = -(int)current_steps.z;
  if( lz < 0 ) lz = 0;
  if( lz > 255 ) lz = 255;
  laser.run(lz);
}


/*
// acceleration stepping curve
int steps_per_unit;
float units_per_step;
float max_speed = 1.0;  // units per sec
float max_squared = max_speed * max_speed;  // units per sec
float accel = 1.0;  // units/sec^2 accel
int C0;
float FreqFactor = 1000000.0 * 0.676 * 256.0; // delays will be one microsec per step


void init_accel_move( int _steps_per_unit )
{
  steps_per_unit = _steps_per_unit;
  units_per_step = 1.0 / (float)steps_per_unit;

  float tmp = (2.0 * units_per_step ) / accel;
  C0 = round( FreqFactor * sqrt(tmp) );

  int accel_steps_required = round( MaxSquared / (2.0 * Accel * units_per_step) );
}
*/

static void digiWrite( volatile byte * Port, byte Mask, bool State )
{
  if( State ) {
    *Port |= Mask;
  }
  else {
    *Port &= ~Mask;
  }
}

static void digiToggle( volatile byte * Port, byte Mask )
{
  *Port |= Mask;
  *Port &= ~Mask;
}


static bool digiRead( volatile byte * Port, byte Mask )
{
  return ((*Port) & Mask) != 0;
}


const long accelSteps_max = 1000;     // estimated
const byte ddaLoopOverhead = 30;       // estimated microseconds per loop to subtract from delay amount

void dda_move(long micro_delay , byte rapid)
{
  //Serial.print( current_steps.x ); Serial.print(" " ); Serial.print( current_steps.y ); Serial.print(" " ); Serial.println( current_steps.z );
  //Serial.print( target_steps.x  ); Serial.print(" " ); Serial.print( target_steps.y  ); Serial.print(" " ); Serial.println( target_steps.z  );

	//figure out our deltas
	max_delta = max(delta_steps.x, delta_steps.y);
	max_delta = max(delta_steps.z, max_delta);

  if( delta_steps.x == 0 && delta_steps.y == 0 ) rapid = 0; // don't do acceleration for Z - no need

	//init stuff.
	long x_counter = -max_delta/2;
	long y_counter = -max_delta/2;
	long z_counter = -max_delta/2;
	
	//our step flags
	bool x_can_step = 0;
	bool y_can_step = 0;
	bool z_can_step = 0;

	if (micro_delay >= 16383)
		milli_delay = micro_delay / 1000;
	else
		milli_delay = 0;

  long Cn, accelSteps, decelStart;
  if( rapid ) {
    milli_delay = 0;
    Cn = (long)800 << 8;  // initial delay (estimated - larger = slower acceleration)
    micro_delay = Cn >> 8;
    accelSteps = accelSteps_max;
    if( accelSteps > (max_delta>>1)) accelSteps = max_delta>>1;
    decelStart = max_delta - accelSteps;  // step to start decelerating
  }

  int8_t xd = x_direction ? 1 : -1;
  int8_t yd = y_direction ? 1 : -1;
  int8_t zd = z_direction ? 1 : -1;

  //do our DDA line!
  long curStep = 1; // used only during rapid moves, for accel/decel tracking
	do
	{
    x_can_step = can_step(XMIN_PORT, XMIN_MASK, XMAX_PORT, XMAX_MASK, current_steps.x, target_steps.x, x_direction);
		y_can_step = can_step(YMIN_PORT, YMIN_MASK, YMAX_PORT, YMAX_MASK, current_steps.y, target_steps.y, y_direction);

		z_can_step = current_steps.z != target_steps.z; // no limits in Z because the laser is clamped


		if (x_can_step)
		{
			x_counter += delta_steps.x;
			if (x_counter > 0)
			{
        digiWrite( XDIR_PORT, XDIR_MASK , x_direction^1 );
        digiToggle( XSTEP_PORT, XSTEP_MASK );

				x_counter -= max_delta;
				current_steps.x += xd;
			}
		}

		if (y_can_step)
		{
			y_counter += delta_steps.y;
			
			if (y_counter > 0)
			{
        digiWrite( YDIR_PORT, YDIR_MASK , y_direction );
        digiToggle( YSTEP_PORT, YSTEP_MASK );

				y_counter -= max_delta;
			  current_steps.y += yd;
			}
		}
		
		if (z_can_step)
		{
			z_counter += delta_steps.z;

			if (z_counter > 0)
			{
        //if(Z_ENABLE_SERVO==0 && Z_ENABLE_LASER==0){
				//  do_step(Z_STEP_PIN, Z_DIR_PIN, z_direction);
        //}
				z_counter -= max_delta;

				current_steps.z += zd;
        set_laser_power();
			}
		}

		//wait for next step.
		if (milli_delay > 0)
			delay(milli_delay);
		else if( micro_delay > 0 )
			delayMicroseconds(micro_delay);

    if( rapid ) {
      curStep++;
      if( curStep < accelSteps ) {
        Cn -= (Cn << 1) / ((curStep<<2) + 1);
        micro_delay = (Cn >> 8) - ddaLoopOverhead; // tuning value, approximate # usecs taken by the loop
      }
      else if( curStep > decelStart ) {
        long n = curStep - max_delta;
        Cn -= (Cn << 1) / ((n<<2) + 1);
        micro_delay = (Cn >> 8) - ddaLoopOverhead;
      }
      else {
        delayMicroseconds(ddaLoopOverhead);
      }
    }
	}
	while (x_can_step | y_can_step | z_can_step);
	
	//set our points to be the same
  current_funits = target_funits;
  current_steps = target_steps;

  //calculate_fdeltas();
}

void get_circle_dir( int8_t f, int8_t d, int8_t a, int8_t b , int8_t & xd, int8_t & yd )
{
  int binrep = 0;
  xd = yd = 0;
  if(f) binrep = binrep + 4;
  if(a) binrep = binrep + 2;
  if(b) binrep = binrep + 1;
  if(d) binrep = 7 - binrep;  // opposite direction, reverse the cases

  switch(binrep)
  {
    case 0:  yd = -1;  break;
    case 1:  xd = -1;  break;
    case 2:  xd =  1;  break;
    case 3:  yd =  1;  break;
    case 4:  xd =  1;  break;
    case 5:  yd = -1;  break;
    case 6:  yd =  1;  break;
    case 7:  xd = -1;  break;
  }
}

void dda_circle( long micro_delay , long xc, long yc, int8_t dir )
{
  //Serial.print( current_steps.x );  Serial.print("  " );
  //Serial.print( current_steps.y );  Serial.print("  " );
  //Serial.print( xc );  Serial.print("  " );
  //Serial.print( yc );  Serial.println("  " );
  //Serial.print( target_steps.x );  Serial.print("  " );
  //Serial.print( target_steps.y );  Serial.print("  " );
  //Serial.print( dir );  Serial.println("  " );

  dir ^= 1;

  //init stuff
  int64_t xdelt = current_steps.x - xc;
  int64_t ydelt = current_steps.y - yc;
  int64_t x_counter = xdelt * xdelt;
  int64_t y_counter = ydelt * ydelt;
  int64_t radsq = x_counter + y_counter;

  if (micro_delay >= 16383)
    milli_delay = micro_delay / 1000;
  else
    milli_delay = 0;

  int8_t xd, yd;

  do {
    // figure out which direction we have to go
    int64_t fxy = x_counter + y_counter - radsq;
    int8_t f = fxy >= 0;
    int8_t a = xdelt >= 0;
    int8_t b = ydelt >= 0;
    
    get_circle_dir( f, dir, a, b , xd, yd );

    x_direction = xd >= 0;
    y_direction = yd >= 0;

    //Serial.print( current_steps.x );  Serial.print( "  " );  Serial.print( xd );  Serial.print( "  " );
    //Serial.print( current_steps.y );  Serial.print( "  " );  Serial.println( yd );

    if( xd != 0 ) {
      digiWrite( XDIR_PORT, XDIR_MASK , x_direction^1 );
      digiWrite( XSTEP_PORT, XSTEP_MASK, true );
      digiWrite( XSTEP_PORT, XSTEP_MASK, false );

      current_steps.x += xd;
      xdelt += xd;
      x_counter = xdelt * xdelt;
    }

    if( yd != 0 ) {
      digiWrite( YDIR_PORT, YDIR_MASK , y_direction );
      digiWrite( YSTEP_PORT, YSTEP_MASK, true );
      digiWrite( YSTEP_PORT, YSTEP_MASK, false );

      current_steps.y += yd;
      ydelt += yd;
      y_counter = ydelt * ydelt;
    }

    //wait for next step.
    if (milli_delay > 0)
      delay(milli_delay);
    else if( micro_delay > 0 )
      delayMicroseconds(micro_delay);

  } while( (current_steps.x != target_steps.x && current_steps.y != target_steps.y) ||
          abs(current_steps.x - target_steps.x) > 10 || abs(current_steps.y - target_steps.y) > 10 );


  // only one of these loops will actually run...
  if( current_steps.x != target_steps.x ) {
    if( current_steps.x > target_steps.x )
      xd = -1;
    else
      xd = 1;
    x_direction = xd > 0;

    while( current_steps.x != target_steps.x )
    {
      digiWrite( XDIR_PORT, XDIR_MASK , x_direction^1 );
      digiWrite( XSTEP_PORT, XSTEP_MASK, true );
      digiWrite( XSTEP_PORT, XSTEP_MASK, false );
      current_steps.x += xd;

      //wait for next step.
      if (milli_delay > 0)
        delay(milli_delay);
      else if( micro_delay > 0 )
        delayMicroseconds(micro_delay);
    }
  }

  if( current_steps.y != target_steps.y ) {
    if( current_steps.y > target_steps.y )
      yd = -1;
    else
      yd = 1;
    y_direction = yd > 0;

    while( current_steps.y != target_steps.y )
    {
      digiWrite( YDIR_PORT, YDIR_MASK , y_direction );
      digiWrite( YSTEP_PORT, YSTEP_MASK, true );
      digiWrite( YSTEP_PORT, YSTEP_MASK, false );
      current_steps.y += yd;

      //wait for next step.
      if (milli_delay > 0)
        delay(milli_delay);
      else if( micro_delay > 0 )
        delayMicroseconds(micro_delay);
    }
  }

  current_funits.x = target_funits.x;
  current_funits.y = target_funits.y;
}


bool can_step(volatile byte *min_port, byte min_pin, volatile byte * max_port, byte max_pin, long current, long target, byte direction)
{
	//stop us if we're on target
	if (target == current)
		return false;

	//stop us if we're at home and still going 
	else if (!direction && read_switch(min_port, min_pin))
		return false;
	//stop us if we're at max and still going
	else if (direction && read_switch(max_port, max_pin))
		return false;

	//default to being able to step
	return true;
}


bool read_switch(volatile byte * port , byte pin)
{
	//dual read as crude debounce
  if(SENSORS_INVERTING)
	  return !digiRead(port, pin) && !digiRead(port, pin);  // using && here to give preference to LOW signal
  else
    return digiRead(port, pin) && digiRead(port, pin);    // using && here to give preference to LOW signal
}


long to_fsteps(long steps_per_unit, long units)
{
  long intRes = steps_per_unit * (units >> 8);
  long fracRes = steps_per_unit * (units & ((1<<8)-1));

  intRes += fracRes >> 8;
  return intRes >> 10;
}


void set_ftarget(long x, long y, long z)  // Set target location in fixed-point units
{
  target_funits.x = x;
  target_funits.y = y;
  target_funits.z = z;
 
  calculate_fdeltas();
}

void set_fposition(long x, long y, long z)
{
  current_funits.x = x;
  current_funits.y = y;
  current_funits.z = z;

  calculate_fdeltas();
}


void calculate_fdeltas()
{
  //figure our deltas.
  delta_funits.x = abs(target_funits.x - current_funits.x);
  delta_funits.y = abs(target_funits.y - current_funits.y);
  delta_funits.z = abs(target_funits.z - current_funits.z);

  //set our steps current, target, and delta
  //current_steps.x = to_steps(x_funits, current_funits.x);
  //current_steps.y = to_steps(y_funits, current_funits.y);
  //current_steps.z = to_steps(z_funits, current_funits.z);

  target_steps.x = to_fsteps(x_funits, target_funits.x);
  target_steps.y = to_fsteps(y_funits, target_funits.y);
  target_steps.z = to_fsteps(z_funits, target_funits.z);

  delta_steps.x = abs(target_steps.x - current_steps.x);
  delta_steps.y = abs(target_steps.y - current_steps.y);
  delta_steps.z = abs(target_steps.z - current_steps.z);
  
  //what is our direction
  x_direction = (target_funits.x >= current_funits.x);
  y_direction = (target_funits.y >= current_funits.y);
  z_direction = (target_funits.z >= current_funits.z);

  //set our direction pins as well
  digitalWrite(X_DIR_PIN, x_direction^1);
  digitalWrite(Y_DIR_PIN, y_direction);
  digitalWrite(Z_DIR_PIN, z_direction);
}

float prevRate = 0;
float steps_per_second = 0;
float micros_per_step = 0;


long calculate_feedrate_delay(float feedrate)
{
  if( delta_steps.x == 0 && delta_steps.y == 0 ) {
    return 0; // No delay required for Z axis solo movements
  }

  // feedrate probably doesn't change too often, so cache some calculation results
  if( prevRate != feedrate ) {
    prevRate = feedrate;
    steps_per_second = feedrate * (1.0/60.0) * x_units;
    micros_per_step = 1000000.0 / steps_per_second;  // convert to microseconds per steps
  }

  // hypotenuse approximation - ~5.7% max error in x/y, z doesn't contribute anything significant in our usage
  long hi = max( delta_steps.x , delta_steps.y );
  long lo = min( delta_steps.x , delta_steps.y );
  hi = max( hi, delta_steps.z );
  long stepDist = (float)(hi + lo/3);

	long master_steps;

	//find the dominant axis.
	if (delta_steps.x >= delta_steps.y)
	{
		if (delta_steps.z > delta_steps.x)
			master_steps = delta_steps.z;
		else
			master_steps = delta_steps.x;
	}
	else
	{
		if (delta_steps.z > delta_steps.y)
			master_steps = delta_steps.z;
		else
			master_steps = delta_steps.y;
	}

  long res = (long)((stepDist * micros_per_step) / master_steps);
  if( res < 0 ) res = 0;

  return res;
}

long calculate_feedrate_delay_circle(float feedrate , float distance)
{
  float master_steps = x_units * distance;

  //calculate delay between steps in microseconds.  this is sort of tricky, but not too bad.
  //the formula has been condensed to save space.  here it is in english:
  // distance / feedrate * 60000000.0 = move duration in microseconds
  // move duration / master_steps = time between steps for master axis.

  long res = (distance * 60000000.0) / (feedrate * master_steps);
  if( res < 0 ) res = 0;

  return res;
}

long getMaxSpeed()
{
	if (delta_steps.z > 0)
		return calculate_feedrate_delay(FAST_Z_FEEDRATE);
	else
		return calculate_feedrate_delay(FAST_XY_FEEDRATE);
}

