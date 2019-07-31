int data;
const int relay = 11;

void setup() { 
  Serial.begin(9600); //initialize serial COM8 at 9600 baudrate
  pinMode(relay, OUTPUT); //make the Relay the output
  digitalWrite (relay, LOW);
}
 
void loop() {
while (Serial.available()){
  data = Serial.read();
}

if (data == '1')
digitalWrite (relay, HIGH);

else if (data == '0')
digitalWrite (relay, LOW);

}
