//======== CAMADA DE APLICAÇÃO DO NÓ SENSOR
//====== COMANDOS
void App_radio_receive_DL() {
  // Acionamento do LED amarelo se o byte 34 está com valor 1
  if (PacoteDL[16] == 1){
    digitalWrite(LED_AMARELO_PIN, HIGH);
    estado_led_amarelo = 1;
  }
  else{
    digitalWrite(LED_AMARELO_PIN, LOW);
    estado_led_amarelo = 0;
  }

//=============== CHAMA DA APLICAÇÃO DE UL 
  App_radio_send_UL();  // Chama a função da camada de Aplicação de UL
}

//============== COMEÇA A CRIAR O PACOTE DE UL
void App_radio_send_UL() {

  // Neste ponto zeramos o pacote de UL para garantir que ele não está carregando nenhuma informação de comunicação anterior.
  for (int i = 0; i < Tamanho_pacote; i++) {
    PacoteUL[i] = 0;
  }

  // Nível da Bateria 
  uint16_t bateria = analogRead(BAT_PIN); // PIN D32
  float    voltage_bat  = (bateria * 3.3f ) / 4095.0f;
  uint16_t voltBatInt = (uint16_t)(voltage_bat * 100);
  
  // Armazene as informações no PacoteUL[] ele é que será enviado no pacote de UL

    PacoteUL[16] = estado_led_amarelo; //PacoteDL[16]; // Status do Led Ligado/Desligado
    PacoteUL[17] = 1; // Aqui vai um código do tipo de hardware PK-LoRa v31, que no caso é a PK-LoRa código 1
    
    // O ESP32 possui conversor analógico de 12 bits (0 a 4095). 
    // A quebra do valor em dois bytes em função de ser um ADC de 12 bits
    PacoteUL[18] = (luminosidade/256); // 40 -> 2 + 20 + 18 // 2 + 36 + 18 Valor inteiro da divisão da luminosidade por 256
    PacoteUL[19] = (luminosidade%256); // 41 Resto da divisão

    // Tensão da Bateria
    //Pacote_UL[19] = TIPO_SENSOR_BAT;
    PacoteUL[20] = (voltBatInt >> 8) & 0xFF;
    PacoteUL[21] =  voltBatInt       & 0xFF;

    // Temperatura
    int16_t tempInt = temperatura * 100;   
    PacoteUL[22] = (tempInt >> 8) & 0xFF;
    PacoteUL[23] =  tempInt       & 0xFF;

    // Umidade
    uint16_t umidInt = umidade * 100;   
    PacoteUL[24] = (umidInt >> 8) & 0xFF;
    PacoteUL[25] =  umidInt       & 0xFF;

    // GPS
    // Latitude
    int32_t lat = (gps.location.lat()) * 1e6;
    //int32_t lat = -22.999656;
    PacoteUL[26]  = (lat >> 24) & 0xFF;
    PacoteUL[27]  = (lat >> 16) & 0xFF;
    PacoteUL[28] = (lat >> 8)  & 0xFF;
    PacoteUL[29] =  lat        & 0xFF;
    
    // Longitude
    int32_t lon = (gps.location.lng()) * 1e6;
    //int32_t lon = -46.819470;
    PacoteUL[30] = (lon >> 24) & 0xFF;
    PacoteUL[31] = (lon >> 16) & 0xFF;
    PacoteUL[32] = (lon >> 8)  & 0xFF;
    PacoteUL[33] =  lon        & 0xFF;

    // Longitude
    int32_t alt = (gps.altitude.meters());
    //int32_t alt = 790;
    PacoteUL[34] = (alt >> 8)  & 0xFF;
    PacoteUL[35] =  alt        & 0xFF;

  //================== CHAMA A CAMADA DE TRANSPORTE DE UL
  Transp_radio_send_UL();
}

// --- FUNÇÃO GPS ---
void updateGPS() {
   // While there is data in the serial buffer, feed it to TinyGPS++
   while (SerialGPS.available() > 0) {
      gps.encode(SerialGPS.read());
   }
}

// -----------------------------------------------------------------
//  LÊ SENSOR — LDR (ADC 12-bits, Média de 8 amostras)
// -----------------------------------------------------------------
uint16_t readLDR() {
    uint32_t soma = 0;
    for (int i = 0; i < NUM_LEITURA; i++) {
        soma += analogRead(LDR_PIN);
        delay(2);
    }
    return (uint16_t)(soma / 8);
}

// -----------------------------------------------------------------
//  LÊ SENSOR — DHT22 (DATA PIN GPIO13, Média de 4 amostras)
// -----------------------------------------------------------------
bool LE_DHT(float &temperatura, float &umidade) {
  float sumTemp = 0.0f;
  float sumHum  = 0.0f;
  uint8_t valid = 0;

  for (uint8_t i = 0; i < NUM_LEITURA; i++) {
    float t = dht.readTemperature();
    float h = dht.readHumidity();

    if (!isnan(t) && !isnan(h)) {
      sumTemp += t;
      sumHum  += h;
      valid++;
    }
  }

  if (valid == 0) return false;

  temperatura = sumTemp / valid;
  umidade     = sumHum  / valid;
  return true;
}


void update_oled(){

  
    
    // Limapa os dados do Display
    display.clearDisplay();
    
    // Escreve o Título Display
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("Wisstek IoT PKLoRa");
    display.drawLine(0, 12, 128, 12, SSD1306_WHITE);

    // Escreve valor do LDR
    display.setTextSize(1);
    display.setCursor(0, 17);
    display.print("Luminosidade: ");
    display.setTextSize(1);
    display.println(luminosidade); // 1 decimal place

    // Escreve valor da Temperatura
    //display.setTextSize(1);
    //display.setCursor(0, 30);
    display.print("Temperatura : ");
    display.setTextSize(1);
    display.print(temperatura, 1); // 1 decimal place
    display.cp437(true); 
    display.write(167);  // Degree symbol
    display.println("C");

    // Escreve valor da Umidade
    //display.setTextSize(1);
    //display.setCursor(0, 43); //56
    display.print("Umidade     : ");
    display.setTextSize(1);
    display.print(umidade, 1);
    display.println("%");
   
    // Escreve valor LATITUDE e LONGITUDE GPS
    // display.setCursor(0, 56);
    if (gps.location.isValid()) {
      display.print("LAT: "); display.println(gps.location.lat(), 5);
      display.print("LON: "); display.println(gps.location.lng(), 5);
      display.print("ALT: "); display.print(gps.altitude.meters());
    }
    else{
      display.println("BUSCANDO");
      display.print("SATELITES");        
    }
    
    // Escreve o buffer na tela Oled
    display.display();

}

