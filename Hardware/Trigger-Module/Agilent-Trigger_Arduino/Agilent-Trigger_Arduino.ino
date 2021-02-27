const byte interruptPin = 2; // Connect intrruptPin via Switch to GND for PRINCE
const byte interruptPinStop = 3;
unsigned long interval_trigger = 5000;    // Interval in ms between two reliable trigger pulses
int relais[] = {4,6};
unsigned long interval = 1000; //Config puls length has to be shorter than interval_trigger

unsigned long previousMillis = 0; // saves seconds since last change
unsigned long previousMillis_trigger = 0; // saves seconds since last change of trigger
unsigned long previousMillis_trigger_Stop = 0; // saves seconds since last change of stop trigger
volatile int trigbut = 0; // saves state of trigger
bool aktiv = false;
bool last_start = false;

void setup()
{
  Serial.begin(19200); // set up baud rate for serial
  Serial.println("Hello eDAQ-Trigger_Duo3");
  pinMode(interruptPin, INPUT);
  pinMode(interruptPinStop, INPUT);
  attachInterrupt(digitalPinToInterrupt(interruptPin), trigit, CHANGE);
  attachInterrupt(digitalPinToInterrupt(interruptPinStop), trigof, CHANGE);
  for(int i=0; i < 2; i++){
    pinMode(relais[i], OUTPUT);
    digitalWrite(relais[i], HIGH);
    Serial.println(i);
  }
}


void loop() // main program begins
///////////////////////////////////////////////////////////////////////////////////////
{
    
//Trigger
  if ((millis() - previousMillis_trigger > interval_trigger) && trigbut == 1) {
    Serial.println("ON_Start");
    for(int i=0; i < 2; i++){
      digitalWrite(relais[i], LOW);
    }
    previousMillis_trigger = millis();  //save current time
    previousMillis = millis();
    aktiv = true;
    last_start = true;
  }
  if ((millis() - previousMillis_trigger_Stop > interval_trigger) && trigbut == 2 && last_start == true) {
    previousMillis_trigger_Stop = millis();  //save current time
    previousMillis = millis();
    Serial.println("ON_Stop");
    for(int i=0; i < 2; i++){
      digitalWrite(relais[i], LOW);
    }
    aktiv = true;
    last_start = false;
  }
  if (trigbut == 2 && last_start == false) {
    Serial.println("nth Stop cancled");
    trigbut = 0;
  }
  if (aktiv && (millis() - previousMillis > interval)){
    Serial.println("OFF");
    for(int i=0; i < 2; i++)
    {
      digitalWrite(relais[i], HIGH);
    }
    aktiv = false;
    trigbut = 0;
  }
}


void trigit() {
  //if (trigbut == 0){
    trigbut = 1;
    Serial.println("go ");
  //}
}

void trigof() {
  //if (trigbut == 0){
    trigbut = 2;
    Serial.println("STOP ");
  //}
}
