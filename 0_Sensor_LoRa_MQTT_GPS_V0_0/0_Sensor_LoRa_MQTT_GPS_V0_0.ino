/*
  MoT LoRa MQTT Versão Zero | WissTek IoT | Nó Sensor - Framework MQTT
  Última versão: Branquinho, Felipe ,Anderson e Luís Felipe (Adaptado para ESP32 - Kit PKLORa)
*/

//=======================================================================
//                     1 - Bibliotecas
//=======================================================================
#include <SPI.h> // A SPI é usada para conectar o ESP32 com o RFM95
#include <LoRa.h> // Biblioteca do RFM95

// Biblioteca Sensores
#include <Wire.h>           // Inclui a Biblioteca Wire para Oled
#include <Adafruit_GFX.h>   // Inclui a Biblioteca GFX para Oled 
#include <Adafruit_SSD1306.h> // Inclui a Biblioteca OLED SSD1306
#include <DHT.h>            // Inclui a Biblioteca DHT
#include <TinyGPS++.h>      // Inclui a Biblioteca GPS

//=======================================================================
//                     2 - Variáveis e Mapeamento
//=======================================================================

// ============= Pinagem na placa da PK-LoRa da ligação do RFM95 com o ESP32
#define SCK_PIN    5
#define MISO_PIN  19
#define MOSI_PIN  27
#define NSS_PIN   18
#define RST_PIN   14
#define DIO0_PIN  26

// ============= CAMADA FÍSICA
// Parâmetros do LoRa
#define FREQUENCY_IN_HZ       915E6    // LoRa Frequency
#define txPower               14       // TX power in dBm, defaults to 17
#define spreadingFactor       7        // ranges from 6-12,default 7
#define signalBandwidth       125E3    // signal bandwidth in Hz
#define codingRateDenominator 8        // denominator of the coding rate

// OLED configuration
#define SCREEN_WIDTH 128 
#define SCREEN_HEIGHT 64 
#define OLED_RESET    -1 // Reset pin # (or -1 if sharing Arduino reset pin)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Pinos sensor de temperatura e umidade DHT22 AM2302
#define DHTPIN 13     // Define o pino de dados para o sensor DHT
#define DHTTYPE DHT22   // Especifica o tipo do sensor como DHT22

// Inicializa o sensor DHT
DHT dht(DHTPIN, DHTTYPE);

// GPS Setup (UART2)
TinyGPSPlus gps;
HardwareSerial SerialGPS(2); // Use UART2

// Váriáveis utilizadas no código
int RSSI_dBm_DL; // Variável com a potência rádio recebida (RSSI) em dBm
int RSSI_DL;     // Variável de mapeamento da RSSI em um valor de 0 a 255 para colocar no pacote
float SNR_DL;    // Variável com a relação sinal ruído
uint8_t SNR_DL_inteiro; // Variável inteira para enviar a SNR, que será convertida para a SNR original no Python

// ============== CAMADA MAC
#define Tamanho_pacote 36
byte PacoteDL[Tamanho_pacote];
byte PacoteUL[Tamanho_pacote];

// ============= CAMADA DE REDE
// Identificação do sensor e tamanho de pacote
int ID_sensor = 1; // Variável de iIdentificação do sensor que está no pacote de DL byte 8
int ID_gateway;    // Variável com o ID_gateway que estará no pacote de DL byte 10

// ============== CAMADA DE TRANSPORTE
int contador_pkt_DL = 0; // Variável para o contador de pacotes de DL
int contador_pkt_UL = 0; // Variável para o contador de pacotes de UL

// ============= CAMADA DE APLICAÇÃO
// Pinos da PK-LoRa
// Pinos dos LEDs
#define LED_VERMELHO_PIN 15
#define LED_AMARELO_PIN   2
#define LED_VERDE_PIN     4

// Pinos de Entradas Analógicas
#define LDR_PIN 36   // ADC1_CH0 — sensor LDR - PIN VP
int luminosidade; // Variável que vai receber o valor da luminosidade entre 0 e 4095 - ADC 12 bits

// Medido da Bateria
#define BAT_PIN   32  // ADC1_CH4 - Bateria End Device (APP)

// Pino do botão
#define BOTAO_PIN  39   // Pino do Botão - PIN VN

// define número de leituras dos sensores
#define NUM_LEITURA 4

// Variáveis de leitura dos sensores
unsigned long ultima_leitura = 0; 
const unsigned long intervalo_sensores = 200; // Intervalo em milisegundos
float temperatura, umidade;  
bool estado_led_amarelo = 0;

//=======================================================================
//                     3 - Setup de inicialização
//=======================================================================
void setup() {
  Serial.begin(115200);
  //while (!Serial);

  Serial.println("--- Iniciando Nó Sensor ---");

  // --- Inicialização de I/O ---
  pinMode(LED_VERMELHO_PIN, OUTPUT);
  pinMode(LED_AMARELO_PIN, OUTPUT);
  pinMode(LED_VERDE_PIN, OUTPUT);
  
  // Garante que os LEDs iniciem desligados
  digitalWrite(LED_VERMELHO_PIN, LOW);
  digitalWrite(LED_AMARELO_PIN, LOW);
  digitalWrite(LED_VERDE_PIN, LOW);

  // resistores de pull-up/pull-down internos. O seu hardware precisa garantir isso.
  pinMode(BOTAO_PIN, INPUT); 

  // Inicia GPS - Serial UART 2: Baud 9600, Pinos: RX=16, TX=17
  SerialGPS.begin(9600, SERIAL_8N1, 16, 17);

  // Initialize I2C with your specific pins (SDA = 21, SCL = 22)
  Wire.begin(21, 22);

  // Initialize OLED display
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { // 0x3C is common I2C address
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); 
  }
  
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  dht.begin();
  delay(200);


  // Configuração ADC para o LDR
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  pinMode(LDR_PIN, INPUT);

  // --- Inicialização Módulo RF95 (LoRa) ---
  
  // 1. Remapeia e inicializa o barramento SPI com os pinos do seu Kit
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, NSS_PIN);

  // 2. Informa à biblioteca LoRa os pinos de controle
  LoRa.setPins(NSS_PIN, RST_PIN, DIO0_PIN);

  if (!LoRa.begin(FREQUENCY_IN_HZ)) {
    Serial.println("Erro ao iniciar módulo RFM95");
  }
  //LoRa.begin(FREQUENCY_IN_HZ));
  LoRa.setTxPower(txPower);
  LoRa.setSpreadingFactor(spreadingFactor);
  LoRa.setSignalBandwidth(signalBandwidth);
  LoRa.setCodingRate4(codingRateDenominator);


  // Limpa o Display
  display.clearDisplay();
    
  Serial.println("LoRa Inicializado com Sucesso!");
  
  // Pisca o LED Verde para indicar inicialização bem-sucedida
  digitalWrite(LED_VERDE_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_VERDE_PIN, LOW);
}

//=======================================================================
//                     4 - Loop de repetição
//=======================================================================
void loop() {

  unsigned long currentMillis = millis();

  // Lê a cada intervalo_sensores [ms] o valor dos Sensores
  if (currentMillis - ultima_leitura >= intervalo_sensores) {
    // Save the current time as the last update time
    ultima_leitura = currentMillis;

    // Le LDR
    luminosidade = readLDR();

    // Le GPS
    updateGPS(); 

    // Le DTH22
    LE_DHT(temperatura, umidade);

    // Atualiza Display Oled
    update_oled();

  }

  // Função que recebe pacote de DL
  Phy_radio_receive_DL(); 
}