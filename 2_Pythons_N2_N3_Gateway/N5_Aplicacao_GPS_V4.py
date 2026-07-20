# FEE247 - Desenvolvimento de Soluções IoT com LoRa e LoRaWAN
#======= Nível 5 - Aplicação ============
# Extrai luminosidade, bateria, temperatura, umidade, GPS e feedback do LED
# dos dados brutos, calcula médias e grava os arquivos de saída do Nível 4
import time
import os

# Arquivos utilizados pelo nível 5 de aplicação
arquivo_valores = "N4/Dados_Processados/valor_sensores.tmp"
arquivo_media   = "N4/Dados_Processados/media_sensores.txt"
arquivo_led     = "N4/Dados_Processados/estado_led_amarelo.txt"

# ===================== FUNÇÕES DE RECONSTRUÇÃO DE BYTES =====================

def bytes_para_uint16(b_alto, b_baixo):
    return (b_alto * 256) + b_baixo

def bytes_para_int16(b_alto, b_baixo):
    valor = (b_alto * 256) + b_baixo
    if valor >= 32768:
        valor -= 65536
    return valor

def bytes_para_int32(b3, b2, b1, b0):
    valor = (b3 << 24) | (b2 << 16) | (b1 << 8) | b0
    if valor >= 2**31:
        valor -= 2**32
    return valor

while True:

    # Procura o último arquivo de dados brutos gravado no nível 4
    try:
        arquivos = [nome for nome in os.listdir("N4/Dados_Brutos") if nome.endswith(".txt")]
    except FileNotFoundError:
        arquivos = []
    arquivos.sort()

    # Se ainda não existe nenhum arquivo de dados brutos, aguarda e tenta de novo
    if not arquivos:
        time.sleep(1)
        continue
    arquivo_entrada = "N4/Dados_Brutos/" + arquivos[-1]

    # Abre o arquivo de dados brutos
    # (usa try/except pois o N2_N3_MQTT.py pode estar gravando o arquivo
    #  neste exato instante, causando erro de leitura pontual)
    try:
        with open(arquivo_entrada,"r") as arquivo:
            linhas = arquivo.readlines()
    except (FileNotFoundError,PermissionError,OSError):
        time.sleep(1)
        continue

    # Listas que guardam os valores calculados de cada sensor
    luminosidades = []
    baterias      = []
    temperaturas  = []
    umidades      = []
    latitudes     = []
    longitudes    = []
    altitudes     = []
    estados_led   = []

    # Começa em 1 para pular o cabeçalho do arquivo
    for i in range(1,len(linhas)):
        partes = linhas[i].strip().split(",")

        # Ignora linha em branco ou linha incompleta (ex: última linha do
        # arquivo sendo gravada pelo N2_N3_MQTT.py no instante da leitura)
        if len(partes) < 74:
            continue

        # Bytes de uplink ocupam as colunas 38 a 73 (36 bytes) do arquivo
        # bruto. Quando o pacote de uplink é perdido, esses 36 bytes são
        # gravados como 9 (marcador de "pacote perdido"). Nesse caso a
        # linha inteira é descartada, pois não representa uma leitura válida.
        try:
            bytes_uplink = [int(x) for x in partes[39:74]]
        except ValueError:
            continue
        if all(b == 9 for b in bytes_uplink):
            continue

        # No arquivo bruto, os bytes do uplink começam na posição 38
        # (2 colunas de timestamp/contador + 36 bytes de downlink)
        # ou seja: partes[byte_do_pacote + 38]
        try:
             
            # Luminosidade -> UL_B18 / UL_B19 (ADC de 12 bits)
            UL_B18 = int(partes[56])
            UL_B19 = int(partes[57])
            luminosidade = bytes_para_uint16(UL_B18,UL_B19)

            # Bateria -> UL_B20 / UL_B21 (uint16, valor bruto de voltBatInt)
            UL_B20 = int(partes[58])
            UL_B21 = int(partes[59])
            bateria = bytes_para_uint16(UL_B20,UL_B21) / 100.0

            # Temperatura -> UL_B22 / UL_B23 (int16, x100)
            UL_B22 = int(partes[60])
            UL_B23 = int(partes[61])
            temperatura = bytes_para_int16(UL_B22,UL_B23) / 100.0

            # Umidade -> UL_B24 / UL_B25 (uint16, x100)
            UL_B24 = int(partes[62])
            UL_B25 = int(partes[63])
            umidade = bytes_para_uint16(UL_B24,UL_B25) / 100.0

            # Latitude -> UL_B26..UL_B29 (int32, x1e6)
            UL_B26 = int(partes[64])
            UL_B27 = int(partes[65])
            UL_B28 = int(partes[66])
            UL_B29 = int(partes[67])
            latitude = bytes_para_int32(UL_B26,UL_B27,UL_B28,UL_B29) / 1e6

            # Longitude -> UL_B30..UL_B33 (int32, x1e6)
            UL_B30 = int(partes[68])
            UL_B31 = int(partes[69])
            UL_B32 = int(partes[70])
            UL_B33 = int(partes[71])
            longitude = bytes_para_int32(UL_B30,UL_B31,UL_B32,UL_B33) / 1e6

            # Altitude -> UL_B34 / UL_B35 (int16, metros)
            UL_B34 = int(partes[72])
            UL_B35 = int(partes[73])
            altitude = bytes_para_int16(UL_B34,UL_B35)

            # Feedback do LED amarelo -> UL_B16 (0 = apagado, 1 = aceso)
            UL_B16 = int(partes[54])
            
        except (ValueError,IndexError):
            # Linha corrompida (ex: campo não numérico) -> descarta e segue
            continue

        # Só 0 e 1 são estados válidos de feedback do LED. Qualquer outro
        # valor (ex: 9 = marcador de pacote perdido, ou lixo de leitura)
        # é normalizado para -1, que representa "sem leitura válida ainda"
        # e já é tratado como tal no N6_Aplicacao (mostra "Feedback LED: --").
        if UL_B16 in (0,1):
            estado_led = UL_B16
        else:
            estado_led = -1

        luminosidades.append(float(luminosidade))
        baterias.append(bateria)
        temperaturas.append(temperatura)
        umidades.append(umidade)
        latitudes.append(latitude)
        longitudes.append(longitude)
        altitudes.append(altitude)
        estados_led.append(estado_led)

    # Se nenhuma linha válida foi encontrada neste ciclo (arquivo recém
    # criado, só com cabeçalho, ou todas as linhas corrompidas), pula este
    # ciclo em vez de travar tentando acessar luminosidades[-1] etc.
    if not luminosidades:
        time.sleep(1)
        continue

    # ===================== VALORES INSTANTÂNEOS =====================
    # Formato por linha: luminosidade;bateria;temperatura;umidade;latitude;longitude;altitude
    f_val = open(arquivo_valores,"w")
    for i in range(len(luminosidades)):
        linha = str(luminosidades[i]) + ";" + str(baterias[i]) + ";" + \
                str(temperaturas[i]) + ";" + str(umidades[i]) + ";" + \
                str(latitudes[i]) + ";" + str(longitudes[i]) + ";" + str(altitudes[i])
        print(linha,file=f_val)
    f_val.close()

    # ===================== MÉDIAS (luminosidade, temperatura, umidade) =====================
    # Formato por linha: media_luminosidade;media_temperatura;media_umidade
    soma_lum = 0.0
    soma_temp = 0.0
    soma_umid = 0.0
    f_media = open(arquivo_media,"w")
    for i in range(len(luminosidades)):
        soma_lum  = soma_lum  + luminosidades[i]
        soma_temp = soma_temp + temperaturas[i]
        soma_umid = soma_umid + umidades[i]
        media_lum  = round((soma_lum  / (i + 1)),2)
        media_temp = round((soma_temp / (i + 1)),2)
        media_umid = round((soma_umid / (i + 1)),2)
        print(str(media_lum) + ";" + str(media_temp) + ";" + str(media_umid),file=f_media)
    f_media.close()

    # ===================== ESTADO ATUAL (FEEDBACK) DO LED =====================
    f_led = open(arquivo_led,"w")
    f_led.write(str(estados_led[-1]))
    f_led.close()

    print("Arquivo =",arquivo_entrada,
          "| Luminosidade =",luminosidades[-1],
          "| Bateria =",baterias[-1],
          "| Temperatura =",temperaturas[-1],
          "| Umidade =",umidades[-1],
          "| Lat =",latitudes[-1],
          "| Lon =",longitudes[-1],
          "| Alt =",altitudes[-1],
          "| LED =",estados_led[-1],
          "| Amostras =",len(luminosidades),
          "| Média Lum =",media_lum,
          "| Média Temp =",media_temp,
          "| Média Umid =",media_umid)
    time.sleep(1)
