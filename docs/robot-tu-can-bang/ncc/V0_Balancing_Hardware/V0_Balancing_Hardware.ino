///////////////////////////////////////////////////////////////////////////////////////
//Terms of use
///////////////////////////////////////////////////////////////////////////////////////
//THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
//IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
//FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
//AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
//LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
//OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
//THE SOFTWARE.
///////////////////////////////////////////////////////////////////////////////////////

#include <Wire.h>                                            //Include the Wire.h library so we can communicate with the gyro

int left_motor, throttle_left_motor, throttle_counter_left_motor, throttle_left_motor_memory;
int right_motor, throttle_right_motor, throttle_counter_right_motor, throttle_right_motor_memory;
int receive_counter;
byte receive_byte, receive_buffer[50];
#define gyro_address 0x68                                     //The I2C address of the MPU-6050 is 0x68
int acc_calibration_value = 1000;                            //Enter the accelerometer calibartion value

//Various settings
float pid_p_gain = 15;                                       //Gain setting for the P-controller (15)
float pid_i_gain = 1.5;                                      //Gain setting for the I-controller (1.5)
float pid_d_gain = 30;                                       //Gain setting for the D-controller (30)
float pid_max_output = 400;                                  //Maximum output of the PID-controller (+/-)

byte start, received_byte;

int error_counter;

int16_t gyro_raw;
int16_t acc_raw;

int16_t gyro_pitch_data_raw;
int32_t gyro_pitch_cal_value;
int16_t acc_x, acc_y, acc_z;
int32_t acc_total_vector;

int32_t cal_int;

float angle_gyro, angle_acc, angle, self_balance_pid_setpoint;

void setup(){
  Serial.begin(9600);                                        //Start the serial port at 9600 kbps
  Wire.begin();                                              //Start the I2C bus as master
  TWBR = 12;                                                 //Set the I2C clock speed to 400kHz

  //By default the MPU-6050 rev A sub-address is 0x68.
  //If you have a rev B you need to change this to 0x69
  //For more information: http://www.invensense.com/mems/gyro/documents/RM-MPU-6000A.pdf
  
  Wire.beginTransmission(gyro_address);                        //Start communication with the address found during search.
  Wire.write(0x6B);                                            //We want to write to the PWR_MGMT_1 register (6B hex)
  Wire.write(0x00);                                            //Set the requested register to 00000000 to start the gyro
  Wire.endTransmission();                                      //End the transmission with the gyro.

  Wire.beginTransmission(gyro_address);                        //Start communication with the address found during search.
  Wire.write(0x1B);                                            //We want to write to the GYRO_CONFIG register (1B hex)
  Wire.write(0x00);                                            //Set the requested register to 00000000 (250dps full scale)
  Wire.endTransmission();                                      //End the transmission with the gyro.

  Wire.beginTransmission(gyro_address);                        //Start communication with the address found during search.
  Wire.write(0x1C);                                            //We want to write to the ACCEL_CONFIG register (1A hex)
  Wire.write(0x08);                                            //Set the requested register to 00001000 (+/- 4g full scale range)
  Wire.endTransmission();                                      //End the transmission with the gyro.

  //Set some filtering to improve the raw data.
  Wire.beginTransmission(gyro_address);                        //Start communication with the address found during search.
  Wire.write(0x1A);                                            //We want to write to the CONFIG register (1A hex)
  Wire.write(0x03);                                            //Set the requested register to 00000011 (Set Digital Low Pass Filter to ~43Hz)
  Wire.endTransmission();                                      //End the transmission with the gyro.

  pinMode(4, OUTPUT);                                          //Configure digital poort 4 as output
  pinMode(5, OUTPUT);                                          //Configure digital poort 5 as output
  pinMode(6, OUTPUT);                                          //Configure digital poort 6 as output
  pinMode(7, OUTPUT);                                          //Configure digital poort 7 as output
  pinMode(13, OUTPUT);                                         //Configure digital poort 13 as output

  print_test();                                                //Print the test on the serial monitor
}

void print_test(){
  Serial.println("=======================================================");
  Serial.println("Starting the test");
  Serial.println("=======================================================");

  Serial.print("Checking I2C address: ");
  Wire.beginTransmission(gyro_address);                        //Start communication with the address found during search.
  error_counter = Wire.endTransmission();                      //End the transmission and get the error code
  if(error_counter == 0)Serial.println("OK");                  //If the error code is 0 the test passed
  else{
    Serial.println("FAILED");                                  //If the error code is not 0 the test failed
    while(1)delay(10);                                         //Stay in this loop because there is no gyro found
  }

  Serial.print("Checking gyro register 0x75: ");
  Wire.beginTransmission(gyro_address);                        //Start communication with the address found during search.
  Wire.write(0x75);                                            //We want to write to the WHO_AM_I register (75 hex)
  Wire.endTransmission();                                      //End the transmission with the gyro.
  Wire.requestFrom(gyro_address, 1);                           //Request 1 bytes from the gyro
  while(Wire.available() < 1);                                 //Wait until the byte is ready
  byte who = Wire.read();
  if(who != 0x68 && who != 0x72){                              //Check if the value is 0x68 or 0x72 (Fact f-nguoi-86450419)
    Serial.println("NO_MPU-6050_FOUND");                       //Print text to screen
    while(1)delay(10);                                         //Stay in this loop because there is no gyro found
  }
  else Serial.println("OK");

  Serial.print("Checking gyro register 0x6B: ");
  Wire.beginTransmission(gyro_address);                        //Start communication with the address found during search.
  Wire.write(0x6B);                                            //We want to write to the PWR_MGMT_1 register (6B hex)
  Wire.endTransmission();                                      //End the transmission with the gyro.
  Wire.requestFrom(gyro_address, 1);                           //Request 1 bytes from the gyro
  while(Wire.available() < 1);                                 //Wait until the byte is ready
  if(Wire.read() != 0x00){                                     //Check if the value is 0x00
    Serial.println("FAILED");                                  //Print text to screen
    while(1)delay(10);                                         //Stay in this loop because there is no gyro found
  }
  else Serial.println("OK");

  Serial.print("Checking gyro register 0x1A: ");
  Wire.beginTransmission(gyro_address);                        //Start communication with the address found during search.
  Wire.write(0x1A);                                            //We want to write to the CONFIG register (1A hex)
  Wire.endTransmission();                                      //End the transmission with the gyro.
  Wire.requestFrom(gyro_address, 1);                           //Request 1 bytes from the gyro
  while(Wire.available() < 1);                                 //Wait until the byte is ready
  if(Wire.read() != 0x03){                                     //Check if the value is 0x03
    Serial.println("FAILED");                                  //Print text to screen
    while(1)delay(10);                                         //Stay in this loop because there is no gyro found
  }
  else Serial.println("OK");

  Serial.print("Checking gyro register 0x1B: ");
  Wire.beginTransmission(gyro_address);                        //Start communication with the address found during search.
  Wire.write(0x1B);                                            //We want to write to the GYRO_CONFIG register (1B hex)
  Wire.endTransmission();                                      //End the transmission with the gyro.
  Wire.requestFrom(gyro_address, 1);                           //Request 1 bytes from the gyro
  while(Wire.available() < 1);                                 //Wait until the byte is ready
  if(Wire.read() != 0x00){                                     //Check if the value is 0x00
    Serial.println("FAILED");                                  //Print text to screen
    while(1)delay(10);                                         //Stay in this loop because there is no gyro found
  }
  else Serial.println("OK");

  Serial.print("Checking gyro register 0x1C: ");
  Wire.beginTransmission(gyro_address);                        //Start communication with the address found during search.
  Wire.write(0x1C);                                            //We want to write to the ACCEL_CONFIG register (1C hex)
  Wire.endTransmission();                                      //End the transmission with the gyro.
  Wire.requestFrom(gyro_address, 1);                           //Request 1 bytes from the gyro
  while(Wire.available() < 1);                                 //Wait until the byte is ready
  if(Wire.read() != 0x08){                                     //Check if the value is 0x08
    Serial.println("FAILED");                                  //Print text to screen
    while(1)delay(10);                                         //Stay in this loop because there is no gyro found
  }
  else Serial.println("OK");
  
  Serial.println("Starting Gyro calibration");
  for (receive_counter = 0; receive_counter < 500; receive_counter++){
    if(receive_counter % 15 == 0)digitalWrite(13, !digitalRead(13));
    Wire.beginTransmission(gyro_address);
    Wire.write(0x43);
    Wire.endTransmission();
    Wire.requestFrom(gyro_address, 4);
    cal_int += Wire.read()<<8|Wire.read();
    gyro_pitch_cal_value += Wire.read()<<8|Wire.read();
    delay(4);
  }
  cal_int /= 500;
  gyro_pitch_cal_value /= 500;
  
  Wire.beginTransmission(gyro_address);
  Wire.write(0x3F);
  Wire.endTransmission();
  Wire.requestFrom(gyro_address, 2);
  acc_z = Wire.read()<<8|Wire.read();
  acc_calibration_value = acc_z;
  Serial.print("Balance value: ");
  Serial.println(acc_calibration_value);
}

void loop(){
  //Keep reading the sensor and print the value on the screen
  Wire.beginTransmission(gyro_address);                        //Start communication with the gyro
  Wire.write(0x3F);                                            //Start reading at register 3F
  Wire.endTransmission();                                      //End the transmission
  Wire.requestFrom(gyro_address, 2);                           //Request 2 bytes from the gyro
  
  acc_z = Wire.read()<<8|Wire.read();                          //Combine the two bytes to make one integer
  acc_z -= cal_int;                                            //Add the accelerometer zero-point offset
  
  if(acc_z > 8200)acc_z = 8200;                               //Limit the accelerator value to the maximum values
  if(acc_z < -8200)acc_z = -8200;                              //Limit the accelerator value to the maximum values
  
  acc_total_vector = sqrt((acc_x*acc_x)+(acc_y*acc_y)+(acc_z*acc_z));  //Calculate the total accelerometer vector
  
  if(abs(acc_y) < acc_total_vector){                           //Prevent the asin function to produce a NaN
    angle_acc = asin((float)acc_y/acc_total_vector)* 57.296;   //Calculate the pitch angle
  }
  
  Serial.print("Angle: ");
  Serial.println(angle_acc);
  delay(100);
}
