# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Generar diagramas actuales de arquitectura y conexiones de PetCare.
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).resolve().parent
W, H = 1600, 1100
BG = "#F4F7FB"
INK = "#14243A"
MUTED = "#536579"
BLUE = "#DCEBFA"
BLUE_EDGE = "#3076B7"
GOLD = "#FFF1D2"
GOLD_EDGE = "#D38C16"
GREEN = "#DFF3E9"
GREEN_EDGE = "#30855D"
PINK = "#FBE3E0"
PINK_EDGE = "#BF5C50"
WHITE = "#FFFFFF"
GRAY = "#DFE6EF"

FONT = Path("C:/Windows/Fonts/arial.ttf")
FONT_B = Path("C:/Windows/Fonts/arialbd.ttf")


def f(size, bold=False):
    return ImageFont.truetype(str(FONT_B if bold else FONT), size)


def wrap(draw, text, font, width):
    out = []
    for paragraph in text.splitlines() or [text]:
        line = ""
        for word in paragraph.split():
            candidate = (line + " " + word).strip()
            if draw.textbbox((0, 0), candidate, font=font)[2] <= width:
                line = candidate
            else:
                if line:
                    out.append(line)
                line = word
        out.append(line)
    return out


def box(draw, rect, fill, outline, radius=24, width=4):
    draw.rounded_rectangle(rect, radius=radius, fill=fill, outline=outline, width=width)


def text_block(draw, xy, text, width, size=24, color=INK, bold=False, gap=8):
    x, y = xy
    font = f(size, bold)
    for line in wrap(draw, text, font, width):
        draw.text((x, y), line, font=font, fill=color)
        y += size + gap
    return y


def arrow(draw, start, end, color, width=7):
    draw.line([start, end], fill=color, width=width)
    import math
    a = math.atan2(end[1] - start[1], end[0] - start[0])
    length, spread = 22, .55
    p1 = (end[0] - length * math.cos(a - spread), end[1] - length * math.sin(a - spread))
    p2 = (end[0] - length * math.cos(a + spread), end[1] - length * math.sin(a + spread))
    draw.polygon([end, p1, p2], fill=color)


def title(draw, main, subtitle):
    draw.text((70, 40), main, font=f(46, True), fill=INK)
    draw.text((72, 104), subtitle, font=f(24), fill=MUTED)


def architecture():
    im = Image.new("RGB", (W, 1200), BG)
    d = ImageDraw.Draw(im)
    title(d, "PetCare · arquitectura actual", "Equipo 08 | corte 25 de noviembre de 2026")

    box(d, (60, 235, 420, 495), BLUE, BLUE_EDGE)
    d.text((90, 262), "ESP32-CAM + OV2640", font=f(27, True), fill=INK)
    text_block(d, (90, 320), "Captura JPEG y entrega video HTTP a la PC por Wi-Fi.", 300, 22)
    text_block(d, (90, 414), "No usa conexión UART con la DevKit.", 300, 20, MUTED)

    box(d, (60, 660, 420, 945), GOLD, GOLD_EDGE)
    d.text((90, 688), "ESP32 DevKit", font=f(30, True), fill=INK)
    text_block(d, (90, 750), "HX711 · DHT22 · PIR", 300, 22)
    text_block(d, (90, 800), "MG995 · relevador y bomba · buzzer", 300, 22)
    text_block(d, (90, 870), "Publica telemetría y recibe órdenes MQTT.", 300, 21)

    box(d, (535, 210, 1115, 1030), WHITE, "#AAB9CA", radius=30, width=4)
    d.text((575, 235), "PC · servidor PetCare", font=f(32, True), fill=INK)

    box(d, (580, 315, 1070, 465), BLUE, BLUE_EDGE)
    d.text((610, 335), "Visión", font=f(26, True), fill=INK)
    text_block(d, (610, 385), "OpenCV DNN + MobileNet-SSD confirma perro o persona en varios cuadros.", 425, 20)

    box(d, (580, 500, 1070, 645), GREEN, GREEN_EDGE)
    d.text((610, 520), "MQTT", font=f(26, True), fill=INK)
    text_block(d, (610, 568), "Broker local, puente, telemetría, órdenes y ACK en petcare/equipo8.", 425, 21)

    box(d, (580, 680, 1070, 825), GOLD, GOLD_EDGE)
    d.text((610, 700), "Panel web local", font=f(26, True), fill=INK)
    text_block(d, (610, 748), "Control manual de alimento, agua, buzzer y compuerta. Deslizador entre 850 y 1500 us.", 425, 20)

    box(d, (580, 860, 1070, 965), "#F1E8FA", "#8361A9")
    d.text((610, 878), "Cloud Firestore · REST", font=f(25, True), fill=INK)
    d.text((610, 922), "Guarda lecturas y eventos, no guarda video.", font=f(20), fill=MUTED)

    box(d, (1210, 370, 1535, 560), PINK, PINK_EDGE)
    d.text((1240, 395), "Teléfono", font=f(29, True), fill=INK)
    text_block(d, (1240, 450), "Abre el panel con la IP de la PC y el mismo Wi-Fi.", 255, 22)

    box(d, (1210, 760, 1535, 950), WHITE, "#AAB9CA")
    d.text((1240, 785), "Firestore", font=f(29, True), fill=INK)
    text_block(d, (1240, 840), "Historial en la nube con autenticación. La PC conserva las credenciales.", 255, 21)

    arrow(d, (420, 350), (580, 385), BLUE_EDGE)
    d.text((425, 300), "HTTP video", font=f(18, True), fill=BLUE_EDGE)
    arrow(d, (420, 805), (580, 565), GOLD_EDGE)
    d.text((430, 635), "MQTT", font=f(19, True), fill=GOLD_EDGE)
    arrow(d, (1070, 735), (1210, 470), PINK_EDGE)
    d.text((1080, 610), "HTTP local", font=f(18, True), fill=PINK_EDGE)
    arrow(d, (1070, 912), (1210, 855), "#8361A9")

    d.text((65, 1080), "La ESP32-CAM, la DevKit y la PC comparten una red Wi-Fi local de 2.4 GHz.", font=f(19), fill=MUTED)
    im.save(OUT / "arquitectura.png", optimize=True)


def wiring():
    im = Image.new("RGB", (W, 1420), BG)
    d = ImageDraw.Draw(im)
    title(d, "PetCare · cableado de baja tensión", "Guía de señales y retornos | protoboard para señales, no para corriente de motor")

    box(d, (55, 175, 435, 450), GOLD, GOLD_EDGE)
    d.text((85, 205), "Fuente regulada 5 V", font=f(27, True), fill=INK)
    d.text((90, 275), "V+  → +5 V cargas", font=f(23, True), fill="#BD3F36")
    d.text((90, 325), "V−  → GND común", font=f(23, True), fill="#252D38")
    text_block(d, (90, 375), "Tierra de protección: no usar como GND del protoboard.", 300, 19, "#6B5A48", True)

    box(d, (540, 175, 1000, 465), BLUE, BLUE_EDGE)
    d.text((570, 205), "ESP32 DevKit", font=f(30, True), fill=INK)
    text_block(d, (580, 270), "GPIO4  DHT22 DATA\nGPIO27  PIR OUT\nGPIO19  HX711 DT\nGPIO18  HX711 SCK\nGPIO33  MG995 señal\nGPIO23  relé IN1\nGPIO22  buzzer señal", 385, 19, gap=5)

    box(d, (55, 540, 435, 1010), WHITE, "#AAB9CA")
    d.text((85, 570), "Sensores", font=f(29, True), fill=INK)
    text_block(d, (85, 630), "DHT22", 310, 21, INK, True)
    text_block(d, (85, 665), "VCC 3V3; DATA GPIO4; GND.", 310, 19, gap=6)
    text_block(d, (85, 735), "PIR", 310, 21, INK, True)
    text_block(d, (85, 770), "OUT GPIO27; VCC según módulo; GND común. OUT máximo 3.3 V.", 310, 18, gap=5)
    text_block(d, (85, 865), "HX711", 310, 21, INK, True)
    text_block(d, (85, 900), "VCC 3V3; DT 19; SCK 18; GND. Celda a E+/E− y A+/A− según etiquetas.", 310, 17, gap=4)

    box(d, (540, 540, 1000, 960), "#E6F3EA", GREEN_EDGE)
    d.text((575, 570), "Protoboard · señales", font=f(27, True), fill=INK)
    text_block(d, (585, 635), "Riel +3V3 ← 3V3 DevKit.\nRiel GND ← GND DevKit + V− fuente.", 375, 20, gap=6)
    text_block(d, (585, 750), "El retorno común es V−, no la tierra de protección.", 375, 19, gap=6)
    text_block(d, (585, 825), "Revisa continuidad de rieles. Lleva la potencia del servo y bomba por cables directos, no por los contactos finos.", 375, 19, gap=6)

    box(d, (1080, 175, 1535, 465), PINK, PINK_EDGE)
    d.text((1110, 205), "MG995 · compuerta", font=f(27, True), fill=INK)
    text_block(d, (1110, 265), "Rojo → +5 V. Café/negro → V−. Naranja/amarillo → GPIO33.", 375, 20)
    text_block(d, (1110, 365), "V− también va a GND DevKit. Límites: abierto 850 us y cerrado 1500 us.", 375, 20)

    box(d, (1080, 540, 1535, 1000), WHITE, "#AAB9CA")
    d.text((1110, 570), "Relevador K1 + bomba", font=f(27, True), fill=INK)
    text_block(d, (1110, 630), "Con el puente VCC–RY-VCC retirado: RY-VCC +5 V; VCC 3V3; GND común; IN1 GPIO23.", 375, 19, gap=5)
    text_block(d, (1110, 765), "+5 V → COM; NO → positivo de bomba; negativo de bomba → V−. Confirma etiquetas COM/NO.", 375, 19, gap=5)
    text_block(d, (1110, 895), "1N4007 paralelo: franja al positivo; sin franja al negativo de la bomba.", 375, 19, "#B7473E", True, gap=5)

    box(d, (55, 1025, 435, 1220), "#F1E8FA", "#8361A9")
    d.text((85, 1050), "Buzzer pasivo", font=f(25, True), fill=INK)
    text_block(d, (85, 1100), "S a GPIO22; VCC y GND según la serigrafía del módulo.", 310, 21)

    box(d, (540, 1025, 1535, 1220), "#EDF1F6", "#9BA9B8")
    d.text((570, 1050), "Punto clave de fuente", font=f(25, True), fill=INK)
    text_block(d, (570, 1100), "La tierra de protección no es el negativo de 5 V. Conecta V− a GND común. Para alimentar la DevKit desde VIN, desconecta USB; nunca unas ambas fuentes. V+ va solo a cargas de 5 V.", 900, 21)

    # V+ solo alimenta cargas de 5 V; no se representa como alimentación a un GPIO.
    arrow(d, (435, 400), (540, 720), "#252D38", 6)
    arrow(d, (1000, 340), (1080, 340), BLUE_EDGE, 5)
    arrow(d, (1000, 420), (1080, 700), GOLD_EDGE, 5)
    im.save(OUT / "diagrama.png", optimize=True)


if __name__ == "__main__":
    architecture()
    wiring()\n