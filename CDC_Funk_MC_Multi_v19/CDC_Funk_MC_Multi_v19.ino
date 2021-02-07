//Packeges
#include <SBNetwork_config.h>
#include <SBNetwork.h>
#include <Wire.h>
//#include <MemoryFree.h>

// *****Config-Start*****

// Set Network role
bool client = !true; // Save bool for client/master
bool ce_ms = !true; //Set Trigger conditions for use with CE-MS (Agilent). require special trigger-board and 4 wire connection
bool onlytrigger = !true; //true, if a dedicated Arduino is used for triggering
bool differential = !true; // Set differential mode
bool temp_on = !true; //toggle for temperatursensor NOT RECOMMENDED
SBNetwork networkDevice(client, 10, 9); // Create a new network device with Arduino and set the _ce and _cs pin. The first argument defines the type of the device. false=master and true=client device

//Trigger config
const byte interruptPin = 2; // Connect intrruptPin via Switch to GND. For use with PRINCE
const byte interruptPinStop = 3;
unsigned long interval_trigger = 5000;    // Interval in ms between two reliable trigger pulses
unsigned long trigbut_reset = 500;  // sets trigbut to 0 trigbut_reset seconds before the next reliable trigger pulses, must be shorter than interval_trigger,
String trigger_tag = String("Tri"); //Identifier for a trigger event

//Config waiting time in ms between reading sensor
unsigned long interval = 10;

//Detector-Identifier
String identifier = String("CDC"); //3 letters for identification;
int cdc_int = 1; //preset for id of CDC, overwritten by switches

//Voltage tracking of supply voltage
const int battary = A0;  // Analog input pin voltage tracking

// Switch for Testing without AD7765 true-> no AD7765
bool debugging = false;
const int analogInPin = A1;  // Analog input pin for Debugging


//////////////////////////////////////////////
//define pins for dip switches (id + Network + ExtraDip) 
#define SelectPinNet 8 //Pin for network toggle
//Pins for id
#define SelectPinA 5 //add 1 to id
#define SelectPinB 6 //add 2 to id 
#define SelectPinC 7 //add 4 to id
//Extra Pin (reserved)
#define ExtraPin 4

/////////////////////////////////////////////


// *****Config-End*****


//Define Values for temp data
String detector = identifier;
bool Network = false;
bool SetupRadio = false;
unsigned long previousMillis = 0; // saves seconds since last change
unsigned long previousMillis_trigger = 0; // saves seconds since last change of trigger
unsigned long previousMillis_trigger_Stop = 0; // saves seconds since last change of stop trigger
unsigned long previousMillis_interrupt = 0; // saves seconds since last interrupt
volatile int trigbut = 0; // saves state of trigger
char det_char[5]; // saves detector identifier in a char
String c_str="";
byte calibration;
byte calibrationB;
int calibrationD;
byte outOfRangeCount = 0;
unsigned long offset = 0; 
long ValueReadFromSensor = 0; //SensorValue
long Temp = 8388608L; //Results in 0 after conversion to C by (X/2048)-4096
int deb_sensorValue = 0; //Value for debugging
long clibNo = 0;
bool last_start = false;
/*

Have option to change between pins 3/7/8 and 4/9/10, since the AD7746 has two capacitance inputs

AD7746 pinout:

Pin 1 SCL
Pin 2 !RDY
Pin 3 EXCA
Pin 4 EXCB
Pin 5 REFIN+
Pin 6 REFIN-
Pin 7 CIN1-
Pin 8 CIN1+
Pin 9 CIN2+
Pin 10 CIN2-
Pin 11 VIN+
Pin 12 VIN-
Pin 13 GND
Pin 14 VDD
Pin 15 NC
Pin 16 SDA
*/
// i2c pins are 4 and 5 for Uno/Nano, 20 and 21 for Mega (SDA/SCL)


/////////////////////////////////////////////////////////////
//AD7746 definitions

#define I2C_ADDRESS  0x48 //0x90 shift one to the right

#define REGISTER_STATUS 0x00
#define REGISTER_CAP_DATA 0x01
#define REGISTER_VT_DATA 0x04
#define REGISTER_CAP_SETUP 0x07
#define REGISTER_VT_SETUP 0x08
#define REGISTER_EXC_SETUP 0x09
#define REGISTER_CONFIGURATION 0x0A
#define REGISTER_CAP_DAC_A 0x0B
#define REGISTER_CAP_DAC_B 0x0C
#define REGISTER_CAP_OFFSET 0x0D
#define REGISTER_CAP_GAIN 0x0F
#define REGISTER_VOLTAGE_GAIN 0x11
#define RESET_ADDRESS 0xBF
#define VALUE_UPPER_BOUND 16777214L 
#define VALUE_ZERO_FARADS 8388607L
#define MAX_OFFSET_ABOVE_ZERO 600000L
#define VALUE_LOWER_BOUND 0xFL
#define MAX_OUT_OF_RANGE_COUNT 3
#define CALIBRATION_INCREASE 1

/////////////////////////////////////////////////////////////
//Configuation Manual for AD7745

//  Capacitive channel setup (REGISTER_CAP_SETUP 0x07)
        // _BV(7)=1 (CAPEN) enables capacitive channel for single conversion, continuous conversion, or calibration
        // _BV(6)=1 (CIN2) switches the internal multiplexer to the second capacitive input on the AD7746.
        // _BV(5)=1 (CAPDIFF) sets differential mode on the selected capacitive input
        // _BV(4) to _BV(1)=0 .
        // _BV(0)=1 (CAPCHOP) The CAPCHOP bit should be set to 0 for the specified capacitive channel performance. CAPCHOP = 1 approximately doubles the capacitive channel conversion times and slightly improves the capacitive channel noise performance for the longest conversion times.

//Voltage/Temperature channel setup (REGISTER_VT_SETUP 0x08)
       // _BV(7) = 1 (VTEN)  enables voltage/temperature channel for single conversion, continuous conversion, or calibration
       // _BV(6) (VTMD1) and _BV(5) (VTMD0) Voltage/temperature channel input configuration. 
          //                                     _BV(6)   _BV(5)    Channel Input 
          //                                     0        0         Internal temperature sensor 
          //                                     0        1         External temperature sensor diode (Transistor 2N3906)
          //                                     1        0         VDD monitor
          //                                     1        1         External voltage input (VIN)
       // _BV(4)=1 (EXTREF) selects an external reference voltage connected to REFIN(+), REFIN(–) for the voltage input or the VDD monitor.
       // _BV(4)=0 selects the on-chip internal reference. The internal reference must be used with the internal temperature sensor for proper operation.
       // _BV(3) an _BV(2)=0
       // _BV(1)=1 (VTSHORT) internally shorts the voltage/temperature channel input for test purposes.
       // _BV(0)=1 (VTCHOP) sets internal chopping on the voltage/temperature channel. The VTCHOP bit must be set to 1 for the specified voltage/temperature channel performance.       

// Configure Excitation (REGISTER_EXC_SETUP 0x09)
        // _BV(7)=1 (CLKCTRL) decreases the excitation signal frequency and the modulator clock frequency by factor of 2.This also increases the conversion time on all channels (capacitive, voltage, and temperature) by a factor of 2.
        // _BV(6)=1 (EXCON) the excitation signal is present on the output during both capacitance and voltage/temperature conversion. Else: the excitation signal is present on the output only during capacitance channel conversion.
        // _BV(5)=1 (EXCB) or _BV(3)=1 (EXCA) enables EXCB or EXCA pin as the excitation output.
        // _BV(4)=1 (EXCB-) or _BV(2)=1 (EXCA-) enables EXCB or EXCA pin as the inverted excitation output.
        // _BV(1) (EXCLVL1) and _BV(0) (EXCLVL0) set Excitation Voltage Level.   _BV(1)=0 and _BV(0)=0 EXC=VDD/2±VDD/8;
        //                                                                       _BV(1)=0 and _BV(0)=1 EXC=VDD/2±VDD/4;
        //                                                                       _BV(1)=1 and _BV(0)=0 EXC=VDD/2±VDD*3/8; 
        //                                                                       _BV(1)=1 and _BV(0)=1 EXC=VDD/2±VDD/2;

//  Converter update rate and mode of operation setup (REGISTER_CONFIGURATION 0x0A)
        // Voltage/temperature channel digital filter setup
          // _BV(7) (VTF1) and _BV(6) (VTF0) Voltage/temperature channel digital filter setup—conversion time/update rate setup. The conversion times in this table are valid for the CLKCTRL = 0 in the EXC SETUP register. The conversion times are longer by a factor of two for the CLKCTRL = 1.
          //                                     _BV(7)   _BV(6)    Conversion Time (ms)  Update Rate (Hz)  ~3dB Freq (Hz)
          //                                     0        0         20.1                  49.8              26.4
          //                                     0        1         32.1                  31.2              15.9
          //                                     1        0         62.1                  16.1              8.0
          //                                     1        1         122.1                 8.2               4.0
        // Capacitive channel digital filter setup
          // _BV(5) (CAPF2) and _BV(4) (CAPF1) and _BV(3) (CAPF0) Capacitive channel digital filter setup—conversion time/update rate setup. The conversion times in this table are valid for the CLKCTRL = 0 in the EXC SETUP register. The conversion times are longer by factor of two for the CLKCTRL = 1.
          //                                     _BV(5)   _BV(4)  _BV(3)    Conversion Time (ms)  Update Rate (Hz)  ~3dB Freq (Hz)
          //                                     0        0        0         11.0                 90.9              87.2
          //                                     0        0        1         11.9                 83.8              79.0
          //                                     0        1        0         20.0                 50.0              43.6
          //                                     0        1        1         38.0                 26.3              21.8
          //                                     1        0        0         62.0                 16.1              13.1
          //                                     1        0        1         77.0                 13.0              10.5
          //                                     1        1        0         92.0                 10.9               8.9
          //                                     1        1        1        109.6                  9.1               8.0
        // Converter mode of operation setup.
          // _BV(2) (MD2) and _BV(1) (MD1) and _BV(0) (MD0)
          //                                     _BV(2)   _BV(1)  _BV(0)    Mode
          //                                     0        0        0        Idle
          //                                     0        0        1        Continuous conversion
          //                                     0        1        0        Single conversion
          //                                     0        1        1        Power-Down
          //                                     1        0        0        -
          //                                     1        0        1        Capacitance system offset calibration
          //                                     1        1        0        Capacitance or voltage system gain calibration
          //                                     1        1        1        -


void setup()
{

  Wire.begin(); // sets up i2c for operation
  Serial.begin(19200); // set up baud rate for serial
  Serial.println("Firmware:CDC_Funk_MC_Multi_v19");
  //Configuration of dip switches for id (3x) and for activating Network
  pinMode(ExtraPin, INPUT_PULLUP);
  pinMode(SelectPinA, INPUT_PULLUP);
  pinMode(SelectPinB, INPUT_PULLUP);
  pinMode(SelectPinC, INPUT_PULLUP);
  pinMode(SelectPinNet, INPUT_PULLUP);
  //SetupRadio = !digitalRead(ExtraPin); // get stat of radio setup switch
  Network = !digitalRead(SelectPinNet); //get state of network by dip switch
  cdc_int = !digitalRead(SelectPinC)*4 +!digitalRead(SelectPinB)*2 + !digitalRead(SelectPinA) + 1;
  if(!client){
    cdc_int = 0;
    Network = true;
    config_notification();
    Serial.println(F("*** PRESS 'E' to handle the switch of adding new clients")); 
  }
  Serial.print("Hello at CDC");
  Serial.println(cdc_int);
  if(!Network and cdc_int != 8){
    SetupRadio = true;
    Serial.println("SetupRadio is active");
    config_notification();
  }
  else if(!Network and cdc_int == 8){
    Serial.println(F("Please make sure that a detector with power supply is connected to configure CDC8 or use a CDC in USB-only mode, in the latter case CDC is always named CDC1"));
    config_notification();
  }
  //activate trigger from interrupt pin
  if(ce_ms){
    pinMode(interruptPin, INPUT);
    pinMode(interruptPinStop, INPUT);
    Serial.println("Agilent Trigger-Mode (4 wire connection)");
  }else{
    pinMode(interruptPin, INPUT_PULLUP);
    pinMode(interruptPinStop, INPUT_PULLUP);
    Serial.println("Prince Trigger-Mode (2 wire connection)");
  }
  attachInterrupt(digitalPinToInterrupt(interruptPin), trigit, CHANGE);
  attachInterrupt(digitalPinToInterrupt(interruptPinStop), trigof, CHANGE);

  // Initialize the network device
  SBMacAddress deviceMac(0x05, 0x04, 0x04, 0x00, 0x00); // Type in here the mac address of the device. This must be unique within your complete network otherwise the network will not work.
  if(Network and !SetupRadio){
    networkDevice.initialize(deviceMac);
    if(!client){
      networkDevice.enableAutomaticClientAdding(false); // Enables the master to automatically add new clients here: disabled
    }
  }

  //cofigure AD7745 
  if(client and !debugging and !onlytrigger and !SetupRadio){
      Serial.print("Init...");
      Wire.beginTransmission(I2C_ADDRESS); // start i2c cycle
      Wire.write(RESET_ADDRESS); // reset the device
      Wire.endTransmission(); // ends i2c cycle
      delay(10);  //wait a tad for reboot (originally 10)
      
      writeRegister(REGISTER_EXC_SETUP, _BV(6) | _BV(5) | _BV(1) | _BV(0)); // EXC source B; Voltage; LOW: 0, HIGH: VDD
            
      if (differential){
        writeRegister(REGISTER_CAP_SETUP,_BV(7) | _BV(5));//enable conversion/calibration and differential Input
      }else{
        writeRegister(REGISTER_CAP_SETUP,_BV(7)); //enable only conversion/calibration
      }
      Serial.println("Get offset");
      offset = ((unsigned long)readInteger(REGISTER_CAP_OFFSET)) << 8;  
      Serial.print("Factory offset: ");
      Serial.println(offset);
      writeRegister(REGISTER_CONFIGURATION, _BV(7) | _BV(6) | _BV(5) | _BV(4) | _BV(3) | _BV(2) | _BV(0));  // set configuration to calib. mode, slow sample (122.1 µs for Time/Volate and 109.6µs for capacitance)
      delay(50); //wait for calibration (originally 10)
      Serial.print("Cal offset1: ");
      offset = ((unsigned long)readInteger(REGISTER_CAP_OFFSET)) << 8;  
      Serial.println(offset);
     
      Wire.beginTransmission(I2C_ADDRESS); // start i2c cycle
      Wire.write(RESET_ADDRESS); // reset the device
      Wire.endTransmission(); // ends i2c cycle
      delay(10);
      //displayStatus();
      Serial.print("Cal offset2: ");
      offset = ((unsigned long)readInteger(REGISTER_CAP_OFFSET)) << 8;  
      Serial.println(offset);
    
       writeRegister(REGISTER_EXC_SETUP, _BV(6) | _BV(5) | _BV(1) | _BV(0)); // EXC source B; Voltage; LOW: 0, HIGH: VDD
            
      if (differential){
        writeRegister(REGISTER_CAP_SETUP,_BV(7) | _BV(5));//enable conversion/calibration and differential Input
      }else{
        writeRegister(REGISTER_CAP_SETUP,_BV(7)); //enable only conversion/calibration
      }
      if (temp_on==true){
        writeRegister(REGISTER_VT_SETUP,_BV(7) | _BV(0));
      }
      writeRegister(REGISTER_CONFIGURATION, _BV(7) | _BV(6) | _BV(5) | _BV(4) | _BV(3) | _BV(0)); // continuous mode; see: Converter update rate and mode of operation setup
      //displayStatus();
      delay(100);
      if (differential){
        delay(10);
        calibrateD(); //determine automatically the offset 
        //writeRegister(REGISTER_CAP_DAC_A, _BV(7) | XX); /Configure Cap-DAC for CIN+, range: 0-127
        //writeRegister(REGISTER_CAP_DAC_B, _BV(7) | XX); /Configure Cap-DAC for CIN-, range: 0-127
      }else{
        calibrate();
      }
      displayStatus();
      Serial.println("done");
  }
  delay(100);
}


void loop() // main program begins
///////////////////////////////////////////////////////////////////////////////////////
{
  while (Serial.available() > 0){ //Configuration over Serial
      char c = toupper(Serial.read());
      c_str +=  c;
      if (c == '\n'){
        if (c_str[0] == 'N' and isdigit(c_str[2])) { //Change bundle number of client with N and bundle number eg: N-4 for bundle 4
          networkDevice.resetData();
          int bu =  c_str[2]-48; //Bad version for converting ASCII-Number to Int
          SBMacAddress deviceMac(0x05, 0x04, 0x04, bu, cdc_int);
          networkDevice.initialize(deviceMac);
          Serial.println("*****");
          Serial.print("Configuration:");
          if(!client){
            Serial.print("Master client-master-set-number:");
          }else{
            Serial.print("Client client-master-set-number:");
          }
          Serial.print(bu);
          Serial.print(" Device-Number: ");
          Serial.println(cdc_int);
          Serial.println("*****");
        }
        if (c_str[0] == 'E') { //Toggle with 'E' AutomaticClientAdding-Function
          // Only master should handle the switch of adding new clients
          if (!networkDevice.RunAsClient) {
            Serial.println("*****");
            if (networkDevice.isAutomaticClientAddingEnabled()) {
              Serial.println("Deactivating AutomaticClientAdding");
            }
            else {
              Serial.println("Activating AutomaticClientAdding");
            }
            Serial.println("*****");
            networkDevice.enableAutomaticClientAdding(!networkDevice.isAutomaticClientAddingEnabled());        
          }
        }
        if (c_str[0] =='S' and client and !onlytrigger){ // 'S' via serial returns settings of CDC
          displayStatus();
        }
        c_str = "";
      }
    }
    
//// Call this in the loop() function to maintain the network device    
  if(Network and !SetupRadio){ 
      networkDevice.update();
    }
    
//Trigger
  if ((millis() - previousMillis_trigger > interval_trigger) && trigbut == 1) {
    previousMillis_trigger = millis();  //save current time
    previousMillis_interrupt = millis();
    detector = trigger_tag + String(trigbut);
    if(!client){
      Serial.println(detector);
    }
   last_start = true;
  }
  
  if ((millis() - previousMillis_trigger_Stop > interval_trigger) && trigbut == 2 && last_start == true) {
    previousMillis_trigger_Stop = millis();  //save current time
    previousMillis_interrupt = millis();
    detector = trigger_tag + String(trigbut);
    if(!client){
      Serial.println(detector);
    }
    last_start = false;
  }

  if (detector.substring(0,3) == trigger_tag and Network){
    detector.toCharArray(det_char, 5); //convert String to a char
    byte message[5 + (3*4)]; // the first 5 bytes containing the type of the sensor. The 3*4 bytes are needed for the values. float has a length of 32 bits = 4 bytes and we need 3 of them.
    strcpy((char*)message, det_char);
    memcpy((void*)(message + 5), &Temp, sizeof(long));
    memcpy((void*)(message + 5 + 4), &clibNo, sizeof(long));
    memcpy((void*)(message + 5 + 4 + 4), &ValueReadFromSensor, sizeof(long));
    networkDevice.sendToDevice(networkDevice.NetworkDevice.MasterMAC, message, 5 + (3*4));
    Serial.println("Send "+detector);
    detector = identifier;
  }
  if (trigbut == 2 && last_start == false) {
    trigbut = 0;
  }
  if (millis() - previousMillis_interrupt > interval_trigger - trigbut_reset){
    trigbut = 0;
  }
  
  if (onlytrigger) {
     //Blank
  } 
  else if(!client){ //Receive data
    // Check, if there are messages available
    uint8_t messageSize = networkDevice.available();
    if (messageSize > 0) {
      byte* message = (byte*)networkDevice.getMessage();
      if (strncmp((char*)message, "CDC", 3) == 0 or strncmp((char*)message, "Tri", 3) == 0) {
        // We have received a transmission
        long offset, calibration, ValueReadFromSensor;
        memcpy(&Temp, (void*)(message + 5), sizeof(long));
        memcpy(&calibration, (void*)(message + 5 + 4), sizeof(long));
        memcpy(&ValueReadFromSensor, (void*)(message + 5 + 4 + 4), sizeof(long));
        Serial.print((char*)message);
        Serial.print(";");
        Serial.print(Temp);
        Serial.print(";");
        Serial.print(calibration);
        Serial.print(";");
        Serial.println(ValueReadFromSensor);
      }
    }
  }
  else if(client and !SetupRadio) { //detector mode (client)
    //Sensor
    if (millis() - previousMillis > interval) {
        previousMillis = millis();  //save current time
        if(debugging == true){
          calibration=0;
          offset=0;
          // read the analog in value:
          deb_sensorValue = analogRead(analogInPin);
          // map it to the range of the analog out:
          ValueReadFromSensor = map(deb_sensorValue, 0, 1023, 0, 127)*10000000;
        }else{
            ValueReadFromSensor = readValue();
            if (temp_on){Temp = readTemp();}
            else {Temp = analogRead(battary);}
            if ((ValueReadFromSensor<VALUE_LOWER_BOUND) or (ValueReadFromSensor>VALUE_UPPER_BOUND)) {
              outOfRangeCount++;
            }
            if (outOfRangeCount>MAX_OUT_OF_RANGE_COUNT) {
              if (ValueReadFromSensor < VALUE_LOWER_BOUND) {
                calibrate(-CALIBRATION_INCREASE);
                offset = ((unsigned long)readInteger(REGISTER_CAP_OFFSET)) << 8;
              } 
              else {
                calibrate(CALIBRATION_INCREASE);
                offset = ((unsigned long)readInteger(REGISTER_CAP_OFFSET)) << 8;
              }
              outOfRangeCount=0;
            }
        }
        clibNo = (int)calibration;
        if (Network) {
          detector += String(cdc_int); //add id to identifier
        }else{
          detector += String(1); //for USB only use set id "CDC1"
        }
        detector.toCharArray(det_char, 5); //convert String to a char
        detector = identifier;
        Serial.print(det_char);
        Serial.print(";");
        Serial.print(Temp);
        Serial.print(";");
        Serial.print(clibNo);
        Serial.print(";");
        Serial.println(ValueReadFromSensor);
        
        if(Network){
          byte message[5 + (3*4)]; // the first 5 bytes containing the type of the sensor. The 3*4 bytes are needed for the values. float has a length of 32 bits = 4 bytes and we need 3 of them.
          strcpy((char*)message, det_char);
          memcpy((void*)(message + 5), &Temp, sizeof(long));
          memcpy((void*)(message + 5 + 4), &clibNo, sizeof(long));
          memcpy((void*)(message + 5 + 4 + 4), &ValueReadFromSensor, sizeof(long));
          networkDevice.sendToDevice(networkDevice.NetworkDevice.MasterMAC, message, 5 + (3*4));
        }
    }
  }else{
    detector += String(cdc_int); //add id to identifier
        detector.toCharArray(det_char, 5); //convert String to a char
        detector = identifier;
        Serial.println(det_char);
        delay(500);
  }
}


void calibrate (byte direction) 
///////////////////////////////////////////////////////////////////////////////////////
{
  calibration += direction;
  //assure that calibration is in 7 bit range
  calibration &=0x7f;
  writeRegister(REGISTER_CAP_DAC_A, _BV(7) | calibration);
}

void calibrate() 
///////////////////////////////////////////////////////////////////////////////////////
{
  calibration = 0;

  //Serial.println("Cal CapDAC A");

  long value = readValue();

  while (value>VALUE_UPPER_BOUND && calibration < 128) {
    calibration++;
    writeRegister(REGISTER_CAP_DAC_A, _BV(7) | calibration);
    value = readValue();
  }
}

void calibrateB() 
///////////////////////////////////////////////////////////////////////////////////////
{
  calibrationB = 0;

  Serial.println("Cal CapDAC B");

  long value = readValue();
  Serial.print("CalB:");
  Serial.println(calibrationB);
  Serial.println(value);
  while (value>VALUE_ZERO_FARADS && calibrationB < 128) {
    calibrationB++;
    Serial.print("CalB:");
    Serial.println(calibrationB);
    writeRegister(REGISTER_CAP_DAC_B, _BV(7) | calibrationB);
    value = readValue();
    Serial.println(value);
  }
  Serial.println("doneB");
}


void calibrateD() 
///////////////////////////////////////////////////////////////////////////////////////
{
  calibrationD = 0;

  Serial.println("Cal CapDACs");

  long value = readValue();
  Serial.print("CalD:");
  Serial.println(calibrationD);
  Serial.print("Value:");
  Serial.println(value);
  while (value<VALUE_ZERO_FARADS && calibrationD > -128) {
    calibrationD--;
    Serial.print("CalDX:");
    Serial.println(calibrationD);
    writeRegister(REGISTER_CAP_DAC_B, _BV(7) | abs(calibrationD));
    value = readValue();
    Serial.println(value);
  }
  while (value>VALUE_ZERO_FARADS+MAX_OFFSET_ABOVE_ZERO && calibrationD < 128) {
    calibrationD++;
    Serial.print("Ca2D:");
    Serial.println(calibrationD);
    writeRegister(REGISTER_CAP_DAC_A, _BV(7) | abs(calibrationD));
    value = readValue();
    Serial.println(value);
  }
  Serial.println("doneD");
}


long readValue() 
///////////////////////////////////////////////////////////////////////////////////////
{
  long ret = 0;
  uint8_t data[3];

  char status = 0;
  //wait until a conversion is done
  while (!(status & (_BV(0) | _BV(2)))) {
    //wait for the next conversion
    status= readRegister(REGISTER_STATUS);
  }

  unsigned long value =  readLong(REGISTER_CAP_DATA);

  value >>=8;
  //we have read one byte to much, now we have to get rid of it
  ret =  value;

  return ret;
}

long readTemp() 
///////////////////////////////////////////////////////////////////////////////////////
{
  long ret = 0;
  uint8_t data[3];

  //char status = 0;
  //wait until a conversion is done
  //while (!(status & (_BV(1) | _BV(2)))) {
    //wait for the next conversion
  //  status= readRegister(REGISTER_STATUS);
  //}

  unsigned long value =  readLong(REGISTER_VT_DATA);
  value >>=8;
  //we have read one byte to much, now we have to get rid of it
  ret =  value;
  return ret;
}


void displayStatus() 
///////////////////////////////////////////////////////////////////////////////////////
{
  unsigned char data[18];
  
  readRegisters(0,18,data);
  
  Serial.println("\nAD7746 Registers:");
  Serial.print("Status (0x0): ");
  Serial.println(data[0],BIN);
  Serial.print("Cap Data (0x1-0x3): ");
  Serial.print(data[1],BIN);
  Serial.print(".");
  Serial.print(data[2],BIN);
  Serial.print(".");
  Serial.println(data[3],BIN);
  Serial.print("VT Data (0x4-0x6): ");
  Serial.print(data[4],BIN);
  Serial.print(".");
  Serial.print(data[5],BIN);
  Serial.print(".");
  Serial.println(data[6],BIN);
  Serial.print("Cap Setup (0x7): ");
  Serial.println(data[7],BIN);
  Serial.print("VT Setup (0x8): ");
  Serial.println(data[8],BIN);
  Serial.print("EXC Setup (0x9): ");
  Serial.println(data[9],BIN);
  Serial.print("Configuration (0xa): ");
  Serial.println(data[10],BIN);
  Serial.print("Cap Dac A (0xb): ");
  Serial.println(data[11],BIN);
  Serial.print("Cap Dac B (0xc): ");
  Serial.println(data[12],BIN);
  Serial.print("Cap Offset (0xd-0xe): ");
  Serial.print(data[13],BIN);
  Serial.print(".");
  Serial.println(data[14],BIN);
  Serial.print("Cap Gain (0xf-0x10): ");
  Serial.print(data[15],BIN);
  Serial.print(".");
  Serial.println(data[16],BIN);
  Serial.print("Volt Gain (0x11-0x12): ");
  Serial.print(data[17],BIN);
  Serial.print(".");
  Serial.println(data[18],BIN);
  
}


void writeRegister(unsigned char r, unsigned char v)
///////////////////////////////////////////////////////////////////////////////////////
{
  Wire.beginTransmission(I2C_ADDRESS);
  Wire.write(r);
  Wire.write(v);
  Wire.endTransmission();
}

void writeInteger(unsigned char r, unsigned int v) 
///////////////////////////////////////////////////////////////////////////////////////
{
  writeRegister(r,(unsigned byte)v);
  writeRegister(r+1,(unsigned byte)(v>>8));
}

unsigned char readRegister(unsigned char r)
///////////////////////////////////////////////////////////////////////////////////////
{
  unsigned char v;
  Wire.beginTransmission(I2C_ADDRESS);
  Wire.write(r);  // register to read
  Wire.endTransmission();

  Wire.requestFrom(I2C_ADDRESS, 1); // read a byte
  while(Wire.available()==0) {
    // waiting
  }
  v = Wire.read();
  return v;
}

void readRegisters(unsigned char r, unsigned int numberOfBytes, unsigned char buffer[])
///////////////////////////////////////////////////////////////////////////////////////
{
  unsigned char v;
  Wire.beginTransmission(I2C_ADDRESS);
  Wire.write(r);  // register to read
  Wire.endTransmission();

  Wire.requestFrom(I2C_ADDRESS, numberOfBytes); // read a byte
  char i = 0;
  while (i<numberOfBytes) {
    while(!Wire.available()) {
      // waiting
    }
    buffer[i] = Wire.read();
    i++;
  }
}

unsigned int readInteger(unsigned char r) 
///////////////////////////////////////////////////////////////////////////////////////
{
  union {
    char data[2];
    unsigned int value;
  } 
  byteMappedInt;

  byteMappedInt.value = 0;

  Wire.beginTransmission(I2C_ADDRESS); // begin read cycle
  Wire.write(0); //pointer to first cap data register
  Wire.endTransmission(); // end cycle
  //after this, the address pointer is set to 0 - since a stop condition has been sent

  Wire.requestFrom(I2C_ADDRESS,r+2); // reads 2 bytes plus all bytes before the register

    while (!Wire.available()==r+2) {
      ; //wait
    }

  for (int i=r+1; i>=0; i--) {
    uint8_t c = Wire.read();
    if (i<2) {
      byteMappedInt.data[i]= c;
    }
  }

  return byteMappedInt.value;

}

unsigned long readLong(unsigned char r) 
///////////////////////////////////////////////////////////////////////////////////////
{
  union {
    char data[4];
    unsigned long value;
  } 
  byteMappedLong;

  byteMappedLong.value = 0L;

  Wire.beginTransmission(I2C_ADDRESS); // begin read cycle
  Wire.write(0); //pointer to first data register
  Wire.endTransmission(); // end cycle
  //the data pointer is reset anyway - so read from 0 on

  Wire.requestFrom(I2C_ADDRESS,r+4); // reads 2 bytes plus all bytes before the register

    while (!Wire.available()==r+4) {
      ; //wait
    }
  for (int i=r+3; i>=0; i--) {
    uint8_t c = Wire.read();
    if (i<4) {
      byteMappedLong.data[i]= c;
    }
  }

  return byteMappedLong.value;

}

void config_notification(){
  Serial.println(F("Enter 'N_X' to reset the wireless device and set it to client-master-set X"));
}

void trigit() {
  if (trigbut == 0){
    trigbut = 1;
    //Serial.print("go ");
  }
}

void trigof() {
  if (trigbut == 0){
    trigbut = 2;
    //Serial.print("STOP ");
  }
}
