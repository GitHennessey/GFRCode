//Dimmer Control and Thermometer using thermistor
//Libraries
#include "RBDdimmer.h" //https://github.com/RobotDynOfficial/RBDDimmer
using namespace std;

//10K Thermistor Setup
/*thermistor parameters:
 * RT0: 10 000 Ω
 * B: 3977 K +- 0.75%
 * T0:  25 C
 * +- 5%
 */
//These values are in the datasheet
#define RT0 10000   // Ω
#define B 3950      // in kilos (Beta Constant)
#define R0 10000  //R=10KΩ
#define VCC 5    //Supply voltage

//100K Thermistor Array Setup !!NOTE: Same B and VCC
#define RT1 100000   // Ω
#define R1 100000  //R=100KΩ
//--------------------------------------

//Variables
float RT, VR, ln, T0, T1, VRT;
float TX0, TX1, TX2, TX3, TX4, TX5, TX6, TX7;
//End Thermistor Setup

//Dimmer Setup
const int zeroCrossPin  = 2;
const int acdPin  = 3;
// End Dimmer Setup

// Define global variables
bool bTempReached;
bool bMaxTempWarning;
bool bIsStable;
int i, n; 
int iStable; // Number of iterations to verify stability
int power; // Starting power level for dimmer
int wantTempC, wantTempF, tempFDif, currentTempF, maxTempC;
String sendData;

//Objects
dimmerLamp acd(acdPin);
//End Dimmer Setup

     
void setup() {
acd.begin(NORMAL_MODE, OFF); // Stop Dimmer Control
// Reset variable values
bIsStable = 0;
i = 0;
n = 0; 
iStable = 20; // Number of iterations to verify stability
power  = 25; // Starting power level for dimmer
wantTempC = 0;
wantTempF = 0;
maxTempC = 55;
tempFDif = 0;
currentTempF = 0;
bMaxTempWarning = false;
T0 = 25 + 273.15; //Temperature T0 from datasheet, 
                    //conversion from Celsius to kelvin
T1 = 25 + 273.15; //Temperature T1 from datasheet, 
                    //conversion from Celsius to kelvin
           
   //Set Digital Pins to Output (Used to power thermistors)
      //10K Thermistor on D11, 100k Array on D12
    pinMode(11, OUTPUT);
    pinMode(12, OUTPUT);
                                               
   //Init Serial USB
  Serial.begin(115200);

   //User must input Wanted Temp (C) in Python for Serial Monitor
  while(Serial.available() < 1){    
  }
  wantTempC = Serial.parseInt();
  wantTempF = floor(((wantTempC * 1.8) + 32));
  if(wantTempC != 0){
  acd.begin(NORMAL_MODE, ON); // Begin Dimmer Control
  } else {
  acd.begin(NORMAL_MODE, OFF); // Begin Dimmer Control
    if (Serial.available() == 0){      
      Serial.println("&"); // Ping Python temperature reached
      delay(200);
    }
  }
}


void loop() {
  // Get temp and set the Power
  GetTemp();
  if(bMaxTempWarning){
   acd.setPower(0); // setPower(0) for Emergency shutoff 
   Serial.println("@");
   Serial.flush();
  }else{
    if(wantTempC != 0){
     SetPower();
    } 
    if(Serial.peek() == '$') {
     Serial.read();
     WriteTemp(); 
    }
    if(Serial.peek() == '^') { // Emergency shutoff from Python
      acd.setPower(0); // setPower(0) for Emergency shutoff
      bMaxTempWarning = true;
    }
  }
  delay(50);
}


void SetPower(){/*function SetPower*/
 // Set the new power Level
    //Conversion to Farenheit for accuracy
    currentTempF = floor(((TX0 * 1.8) + 32));
    tempFDif = abs(currentTempF - wantTempF);
     
    if(power<75 && currentTempF<(wantTempF - 0.25)) {
      power = power + 1;
    } else if(power>15 && currentTempF>(wantTempF + 0.15)){
      power = power - 1;
    } else if(!bIsStable && tempFDif <= 0.1){
      n++; // Increment n if SetTemp has been reached
           // and temperature hasn't stabilized  yet
    }
    acd.setPower(power); // setPower(0-95%);
   //------------------------ Power Level Adjusted
    if(!bIsStable) {
        WriteTemp();
      if(n==iStable){ // Temperature stable
        bIsStable = 1;
        if (Serial.available() == 0){      
            Serial.println("&"); // Ping Python temperature reached
            delay(200);
        }
    }
   }
}

void CheckMax(float thisTemp) {
  if(thisTemp >= maxTempC){
  bMaxTempWarning = true;
  }
}

void GetTemp(){/*function GetTemp*/
  //Ambient Temp Reading and Display
    digitalWrite(11, HIGH); //Apply 5V to 10K Thermistor Divider
    digitalWrite(12, HIGH); //Apply 5V to 10K Thermistor Divider
    delay(25);
    VRT = analogRead(0); //Acquisition analog value of VRT 
    digitalWrite(11, LOW); //Apply 0V to 10K Thermistor Divider  
    //Conversion to voltage 1023 is Analog Resolution   
    VRT = (5.00 / 1023.00) * VRT;  
    VR = VCC - VRT;                   //Original voltage Reading
    RT = VRT / (VR / R0);             //Resistance of thermistor
    ln = log(RT / RT0);
    TX0 = (1 / ((ln / B) + (1 / T0))); //Temperature from thermistor
    TX0 = TX0 - 273.15;                 //Conversion to Celsius
  //------------------------------ End Ambient Reading
  
  //Battery Temp Readings and Display
    for (i = 1; i < 8; i++){ 
      VRT = analogRead(i); //Acquisition analog value of VRT 
      //Conversion to voltage 1023 is Analog Resolution   
      VRT = (5.00 / 1023.00) * VRT;  
      VR = VCC - VRT;                   
      RT = VRT / (VR / R1);             //Resistance of thermistor
      ln = log(RT / RT1);
      
      switch(i) {
      case 1:
        TX1 = (1 / ((ln / B) + (1 / T1))); //Temperature from thermistor
        TX1 = TX1 - 273.15; //Conversion to Celsius
        CheckMax(TX1);
        break;
      case 2:
        TX2 = (1 / ((ln / B) + (1 / T1))); //Temperature from thermistor
        TX2 = TX2 - 273.15; //Conversion to Celsius
        CheckMax(TX2);
        break;
      case 3:
        TX3 = (1 / ((ln / B) + (1 / T1))); //Temperature from thermistor
        TX3 = TX3 - 273.15; //Conversion to Celsius
        CheckMax(TX3);
        break;
      case 4:
        TX4 = (1 / ((ln / B) + (1 / T1))); //Temperature from thermistor
        TX4 = TX4 - 273.15; //Conversion to Celsius
        CheckMax(TX4);
        break;
      case 5:
        TX5 = (1 / ((ln / B) + (1 / T1))); //Temperature from thermistor
        TX5 = TX5 - 273.15; //Conversion to Celsius
        CheckMax(TX5);
        break;
      case 6:
        TX6 = (1 / ((ln / B) + (1 / T1))); //Temperature from thermistor
        TX6 = TX6 - 273.15; //Conversion to Celsius
        CheckMax(TX6);
        break;
      case 7:
        TX7 = (1 / ((ln / B) + (1 / T1))); //Temperature from thermistor
        TX7 = TX7 - 273.15; //Conversion to Celsius
        CheckMax(TX7);
        break;
      }
     }
    digitalWrite(12, LOW); //Apply 0V to 10K Thermistor Divider
  //------------------------------ End Battery Readings
}

void WriteTemp(){/*function WriteTemp*/
      sendData = "";
    sendData += String(TX0);
    sendData += String('\t'); 
    sendData += String(TX1); 
    sendData += String('\t'); 
    sendData += String(TX2); 
    sendData += String('\t'); 
    sendData += String(TX3); 
    sendData += String('\t'); 
    sendData += String(TX4); 
    sendData += String('\t'); 
    sendData += String(TX5); 
    sendData += String('\t'); 
    sendData += String(TX6); 
    sendData += String('\t'); 
    sendData += String(TX7); 
    Serial.println(sendData);
    Serial.flush();
}
