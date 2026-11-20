"""Calibracion guiada aparte. Guarda una propuesta; no cambia la referencia activa."""
import time
import json
import math
from machine import Pin
from hx711 import HX711
from calibracion_pesa import cargar
import config

def medir(hx, factor):
    valores=[]
    inicio=time.ticks_ms()
    while len(valores)<30 and time.ticks_diff(time.ticks_ms(),inicio)<10000:
        valor=hx.read_ready()
        if valor is not None:
            valores.append(valor)
        time.sleep_ms(10)
    if len(valores)<30:
        raise ValueError('HX711 no entrego 30 lecturas; revisar DOUT19, SCK18 y alimentacion 3V3')
    ordenados=sorted(valores)
    centro=sum(ordenados[3:-3])/24
    dispersion=max(valores)-min(valores)
    print('RAW promedio:',centro,'| variacion RAW:',dispersion)
    if dispersion/abs(factor)>3:
        raise ValueError('Lectura inestable: mas de 3 g de variacion. No se guarda nada.')
    return centro

def main():
    Pin(config.PIN_PUMP_RELAY,Pin.OUT,value=1)
    Pin(config.PIN_SERVO,Pin.OUT,value=0)
    Pin(config.PIN_BUZZER,Pin.OUT,value=0)
    cal=cargar()
    if cal['error']:
        print(cal['error']);return
    hx=HX711(config.PIN_HX711_DOUT,config.PIN_HX711_SCK)
    print('PRUEBA APARTE DE PESA. Ejecutar en Thonny con el programa principal detenido.')
    print('Deja apagada la fuente de servo y bomba. Calibracion actual:',cal)
    print('Ninguna opcion modifica calibracion_validada.json.')
    try:
        while True:
            opcion=input('1 Leer 10 s | 2 Calibracion guiada nueva | 0 Salir: ').strip()
            if opcion=='0':return
            try:
                if opcion=='1':
                    inicio=time.ticks_ms();ultimo=inicio
                    while time.ticks_diff(time.ticks_ms(),inicio)<10000:
                        raw=hx.read_ready()
                        if raw is not None and time.ticks_diff(time.ticks_ms(),ultimo)>=500:
                            ultimo=time.ticks_ms()
                            print('RAW:',raw,'| g referencia guardada:',(raw-cal['tara'])/cal['factor'])
                        time.sleep_ms(10)
                elif opcion=='2':
                    input('Deja el tazon VACIO en su soporte, retira las manos y pulsa Enter: ')
                    time.sleep_ms(2000);tara=medir(hx,cal['factor'])
                    texto=input('Masa TOTAL del objeto en gramos, medida en otra bascula (Enter cancela): ').strip()
                    if not texto:continue
                    masa=float(texto.replace(',','.'))
                    if not math.isfinite(masa) or masa<=0:raise ValueError('Masa debe ser positiva')
                    input('Coloca ese objeto dentro del tazon y pulsa Enter: ')
                    time.sleep_ms(2000);carga=medir(hx,cal['factor'])
                    delta=carga-tara
                    if abs(delta)<100:raise ValueError('La respuesta de la celda es demasiado pequena')
                    factor=delta/masa
                    input('Retira el objeto, deja VACIO y pulsa Enter: ')
                    time.sleep_ms(2000);regreso=medir(hx,factor)
                    error_cero=(regreso-tara)/factor
                    if abs(error_cero)>3:raise ValueError('No regreso al cero: %.2f g; no se guarda'%error_cero)
                    input('Vuelve a colocar el MISMO objeto y pulsa Enter: ')
                    time.sleep_ms(2000);repetida=medir(hx,factor)
                    peso=(repetida-tara)/factor
                    if abs(peso-masa)>max(3,masa*0.03):raise ValueError('No repite el peso; no se guarda')
                    print('Propuesta: factor',factor,'tara',tara,'referencia',masa,'repeticion',peso)
                    if input('Escribe GUARDAR para crear propuesta aparte: ').strip()=='GUARDAR':
                        nombre='calibracion_propuesta_%d.json'%time.ticks_ms()
                        with open(nombre,'w') as archivo:
                            json.dump({'CALIBRATION_FACTOR':factor,'TARE_RAW':tara,
                                'masa_referencia_g':masa,'referencia_aproximada':False,
                                'masa_declarada_por_usuario':True,'error_regreso_g':error_cero,
                                'peso_repeticion_g':peso},archivo)
                        print('Guardado:',nombre,'; todavia NO aplicado al programa principal.')
            except (ValueError,OSError) as exc:
                print('Prueba detenida:',exc,'| referencia original intacta')
    except KeyboardInterrupt:
        print('Cancelado; referencia original intacta')

if __name__=='__main__':main()
