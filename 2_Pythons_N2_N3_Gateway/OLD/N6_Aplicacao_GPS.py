# FEE247 - Desenvolvimento de Soluções IoT com LoRa e LoRaWAN
#======= Nível 6 - Aplicação ============
# Gráficos de luminosidade, temperatura e umidade (com médias)
# Texto de bateria e GPS, botão para abrir mapa e botão de comando/feedback do LED
import tkinter as tk
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.style as style
import webbrowser
import os

style.use("ggplot")

MAX_PONTOS = 60
cor_lum   = "#1f77b4"
cor_temp  = "#2ca02c"
cor_umid  = "#9467bd"
cor_media = "#ff7f0e"

# Garante que os diretórios de parâmetros existam
if not os.path.exists("N4"):
    os.mkdir("N4")
if not os.path.exists("N4/parametros"):
    os.mkdir("N4/parametros")

CAMINHO_CMD_LED = "N4/parametros/cmd_led_amarelo.txt"
CAMINHO_VALORES = "N4/Dados_Processados/valor_sensores.tmp"
CAMINHO_MEDIAS  = "N4/Dados_Processados/media_sensores.txt"
CAMINHO_LED_FB  = "N4/Dados_Processados/estado_led_amarelo.txt"

# Última posição de GPS conhecida (usada pelo botão de mapa)
ultima_lat = None
ultima_lon = None

# ===================== LEITURA DOS ARQUIVOS =====================

def ler_valores():
    lum, bat, temp, umid, lat, lon, alt = [], [], [], [], [], [], []
    try:
        with open(CAMINHO_VALORES,"r") as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        partes = linha.split(";")
                        lum.append(float(partes[0]))
                        bat.append(float(partes[1]))
                        temp.append(float(partes[2]))
                        umid.append(float(partes[3]))
                        lat.append(float(partes[4]))
                        lon.append(float(partes[5]))
                        alt.append(float(partes[6]))
                    except (ValueError,IndexError):
                        pass
    except FileNotFoundError:
        pass
    return lum, bat, temp, umid, lat, lon, alt

def ler_medias():
    media_lum, media_temp, media_umid = [], [], []
    try:
        with open(CAMINHO_MEDIAS,"r") as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        partes = linha.split(";")
                        media_lum.append(float(partes[0]))
                        media_temp.append(float(partes[1]))
                        media_umid.append(float(partes[2]))
                    except (ValueError,IndexError):
                        pass
    except FileNotFoundError:
        pass
    return media_lum, media_temp, media_umid

def ler_feedback_led():
    try:
        with open(CAMINHO_LED_FB,"r") as f:
            valor = f.read().strip()
            return int(valor)
    except (FileNotFoundError,ValueError):
        return None

# ===================== COMANDO DO LED =====================

estado_comando_led = tk.IntVar(value=0)

def enviar_comando_led():
    novo_valor = 0 if estado_comando_led.get() == 1 else 1
    estado_comando_led.set(novo_valor)
    with open(CAMINHO_CMD_LED,"w") as f:
        f.write(str(novo_valor))
    btn_led.config(text="Comando LED: " + ("LIGAR" if novo_valor == 0 else "DESLIGAR"))
    print(f"Comando de LED enviado: {novo_valor}")

# ===================== BOTÃO DE MAPA =====================

def abrir_mapa():
    if ultima_lat is None or ultima_lon is None:
        messagebox.showinfo("GPS","Ainda não há coordenadas de GPS disponíveis.")
        return
    url = f"https://www.google.com/maps?q={ultima_lat},{ultima_lon}"
    webbrowser.open(url)

# ===================== ATUALIZA UM SUBPLOT (SENSOR + MÉDIA) =====================

def atualizar_subplot(ax, valores, medias, titulo, unidade, cor_valor):
    valores = valores[-MAX_PONTOS:]
    medias = medias[-MAX_PONTOS:]

    # Ajusta tamanhos diferentes entre valor instantâneo e média
    if len(medias) < len(valores):
        if len(medias) > 0:
            ultimo = medias[-1]
            while len(medias) < len(valores):
                medias.append(ultimo)
        else:
            medias = valores.copy()

    ax.clear()
    if valores:
        ax.plot(valores,label=titulo,linewidth=2,marker='o',markersize=3,color=cor_valor)
        ax.plot(medias,label="Média",linewidth=2.5,color=cor_media)
        ax.legend(loc='upper right',fontsize=8)
        todos = valores + medias
        val_min = min(todos)
        val_max = max(todos)
        margem = (val_max - val_min) * 0.10
        if margem == 0:
            margem = 1
        ax.set_ylim(val_min - margem, val_max + margem)

    ax.set_title(titulo,fontsize=10)
    ax.set_ylabel(unidade,fontsize=9)
    ax.set_xlabel("Últimas " + str(MAX_PONTOS) + " medidas",fontsize=8)

# ===================== ATUALIZA TUDO =====================

def atualizar(canvas, raiz, labels):
    global ultima_lat, ultima_lon

    lum, bat, temp, umid, lat, lon, alt = ler_valores()
    media_lum, media_temp, media_umid = ler_medias()

    # ----- Gráficos -----
    atualizar_subplot(ax_lum, lum, media_lum, "Luminosidade", "Intensidade (0-4095)", cor_lum)
    atualizar_subplot(ax_temp, temp, media_temp, "Temperatura", "°C", cor_temp)
    atualizar_subplot(ax_umid, umid, media_umid, "Umidade", "% UR", cor_umid)
    fig.tight_layout()
    canvas.draw()

    # ----- Textos (bateria e GPS) -----
    if bat:
        labels["bateria"].config(text="Bateria (bruto): " + str(int(bat[-1])))
    if lat and lon:
        ultima_lat = lat[-1]
        ultima_lon = lon[-1]
        labels["gps"].config(text=f"GPS: Lat {lat[-1]:.6f}  |  Lon {lon[-1]:.6f}  |  Alt {alt[-1]:.0f} m")

    # ----- Feedback do LED -----
    fb = ler_feedback_led()
    if fb == 1:
        labels["led_fb"].config(text="Feedback LED: ACESO",bg="#2ca02c")
    elif fb == 0:
        labels["led_fb"].config(text="Feedback LED: APAGADO",bg="#888888")
    else:
        labels["led_fb"].config(text="Feedback LED: --",bg="#888888")

    raiz.after(1000,atualizar,canvas,raiz,labels)

# ===================== BOTÕES DE JANELA =====================

def fechar():
    if messagebox.askokcancel("Sair","Deseja fechar o monitor?"):
        raiz.destroy()

def salvar(fig):
    arquivo = filedialog.asksaveasfilename(defaultextension=".png")
    if arquivo:
        fig.savefig(arquivo)

# ===================== INTERFACE =====================

raiz = tk.Tk()
raiz.title("FEE247 - NÍVEL 6 - APLICAÇÃO")
raiz.geometry("1050x950")

# ----- Textos de bateria e GPS -----
frame_labels = tk.Frame(raiz)
frame_labels.pack(fill="x", padx=10, pady=8)

label_bateria = tk.Label(frame_labels,text="Bateria (bruto): --",font=("Arial",11,"bold"),
                          bg="#555555",fg="white",relief="ridge",bd=3,width=24,pady=6)
label_bateria.pack(side="left",padx=6)

label_gps = tk.Label(frame_labels,text="GPS: --",font=("Arial",11,"bold"),
                      bg="#555555",fg="white",relief="ridge",bd=3,width=46,pady=6)
label_gps.pack(side="left",padx=6)

label_led_fb = tk.Label(frame_labels,text="Feedback LED: --",font=("Arial",11,"bold"),
                         bg="#888888",fg="white",relief="ridge",bd=3,width=22,pady=6)
label_led_fb.pack(side="left",padx=6)

labels = {"bateria": label_bateria, "gps": label_gps, "led_fb": label_led_fb}

# ----- Área dos gráficos (3 subplots empilhados) -----
frame_graficos = tk.Frame(raiz)
frame_graficos.pack(fill="both", expand=True)

fig = Figure(figsize=(10, 8))
ax_lum  = fig.add_subplot(311)
ax_temp = fig.add_subplot(312)
ax_umid = fig.add_subplot(313)

canvas = FigureCanvasTkAgg(fig,master=frame_graficos)
canvas.get_tk_widget().pack(fill="both",expand=True)

# ----- Botões -----
frame_botoes = tk.Frame(raiz)
frame_botoes.pack(pady=8)

btn_salvar = tk.Button(frame_botoes,text="Salvar Gráfico",command=lambda: salvar(fig))
btn_salvar.pack(side="left",padx=8)

btn_mapa = tk.Button(frame_botoes,text="Ver Localização no Mapa",command=abrir_mapa)
btn_mapa.pack(side="left",padx=8)

btn_led = tk.Button(frame_botoes,text="Comando LED: LIGAR",command=enviar_comando_led)
btn_led.pack(side="left",padx=8)

# ----- Início -----
atualizar(canvas,raiz,labels)
raiz.protocol("WM_DELETE_WINDOW",fechar)

raiz.mainloop()
