"""PetCare: programa integrado. No calibra ni ejecuta actuadores al iniciar."""
import time
import config

def main(solo_lectura=False,max_runtime_ms=None):
    from actuadores import ServoSG90,PumpRelay,ActiveBuzzer
    from sensores import SensorHub
    from controlador import PetCareController
    from mqtt_link import MQTTLink
    from wifi_panel import Wifi,WebDashboard
    from pantalla_peso import PantallaPeso
    pump=PumpRelay()
    servo=ServoSG90()
    buzzer=ActiveBuzzer()
    control=PetCareController(SensorHub(),servo,pump,buzzer)
    control.actions_allowed=not solo_lectura
    mqtt=MQTTLink();wifi=Wifi();web=WebDashboard();screen=PantallaPeso()
    start=time.ticks_ms();last_print=start;web_retry=start
    print('\nPetCare',config.VERSION,'| GPIO conservados')
    print('Calibracion:',control.sensors.cal)
    print('Servo 1350/1690 us. Rele D23 activo LOW. Buzzer D22 modo',config.BUZZER_MODE)
    print('No hay tara automatica. Ctrl+C detiene las salidas.')
    try:
        while True:
            now=time.ticks_ms()
            try:status=control.tick(now)
            except Exception as exc:
                pump.off();buzzer.off()
                print('Control:',repr(exc));status=control.snapshot()
            wifi.tick(time.ticks_ms(),not control.action_in_progress())
            mqtt.poll(time.ticks_ms(),control,wifi.connected())
            if wifi.connected() and web.server is None and time.ticks_diff(now,web_retry)>=0:
                web_retry=time.ticks_add(now,15000)
                try:
                    web.start();print('Panel local: http://'+wifi.wlan.ifconfig()[0]+'/')
                except Exception as exc:print('Panel inicio:',repr(exc));web.close()
            web.poll(control,time.ticks_ms())
            if not control.action_in_progress():screen.update(status,control.state,time.ticks_ms())
            if time.ticks_diff(now,last_print)>=3000:
                last_print=now
                print('RAW:',status.get('raw'),'| g:',status.get('weight_g'),
                      '| DHT:',status.get('temperature_c'),status.get('humidity_pct'),
                      '| PIR:',status.get('pir'),'|',control.state)
            if max_runtime_ms is not None and time.ticks_diff(now,start)>=max_runtime_ms:break
            time.sleep_ms(10)
    except KeyboardInterrupt:
        print('Detenido por el usuario')
    finally:
        control.safe_shutdown();mqtt.close();web.close()
        print('Salidas apagadas; calibracion intacta')

if __name__=='__main__':
    main()
