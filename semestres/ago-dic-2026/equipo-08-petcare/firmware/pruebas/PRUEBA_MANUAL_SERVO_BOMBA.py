# PetCare: prueba manual sin esperas bloqueantes ni actuadores simultaneos.
import sys
import time
import config
from actuadores import ServoSG90, PumpRelay

ABRIR_US = 850
CERRAR_US = 1500
BOMBA_MS = 3000
VERSION = 'manual-v2-sin-input'


class ControlManual:
    def __init__(self, pump, servo):
        self.pump, self.servo = pump, servo
        self.servo_manteniendo = False
        self.inicio_bomba = None
        self.terminado = False
        self.error = None

    def detener(self):
        errors = []
        for name, action in (('bomba', self.pump.off), ('servo', self.servo.release)):
            try:
                action()
            except Exception as exc:
                errors.append(name + ': ' + repr(exc))
        self.inicio_bomba = None
        self.servo_manteniendo = False
        if errors:
            self.terminado = True
            raise RuntimeError('; '.join(errors))

    def tick(self, now):
        if self.inicio_bomba is not None:
            elapsed = time.ticks_diff(now, self.inicio_bomba)
            if elapsed >= BOMBA_MS or not self.pump.active:
                self.pump.off()
                self.inicio_bomba = None
                print('CORTE BOMBA: orden OFF a los', elapsed, 'ms; GPIO23 debe quedar HIGH.')

    def comando(self, option, now):
        if self.terminado:
            return False, 'Prueba terminada.'
        try:
            self.tick(now)
            if option == '0':
                self.detener()
                self.terminado = True
                return True, 'Fin; bomba apagada y servo sin PWM.'
            if option == '5':
                self.detener()
                return True, 'Bomba apagada; PWM retirado. Los 5 V del servo siguen conectados.'
            if option == '4':
                self.pump.off()
                self.inicio_bomba = None
                return True, 'Bomba apagada manualmente.'
            if option in ('1', '2'):
                if self.inicio_bomba is not None or self.pump.active:
                    return False, 'Bomba activa: servo bloqueado hasta apagarla.'
                pulse = ABRIR_US if option == '1' else CERRAR_US
                self.servo.move_us(pulse)
                self.servo_manteniendo = True
                return True, 'Orden servo %s us; PWM mantenido.' % pulse
            if option == '3':
                if self.servo_manteniendo:
                    return False, 'Servo con PWM: usa 5 para liberar antes de probar agua.'
                if self.inicio_bomba is not None or self.pump.active:
                    return False, 'Bomba ya activa; no se prolonga el plazo.'
                self.inicio_bomba = now
                self.pump.on(duration_ms=BOMBA_MS)
                return True, 'Bomba ON: corte por reloj y temporizador a los 3 s.'
            return False, 'Usa 0, 1, 2, 3, 4 o 5 y Enter.'
        except Exception as exc:
            self.error = repr(exc)
            self.terminado = True
            try:
                self.detener()
            finally:
                print('ERROR; no se repetira la orden:', self.error)
            return False, self.error


def main():
    import select
    pump = servo = control = None
    previous_min = config.SERVO_MIN_PULSE_US
    try:
        if (config.PIN_SERVO, config.PIN_PUMP_RELAY, config.PUMP_ACTIVE_LEVEL) != (33, 23, 0):
            raise ValueError('Revisar pines: servo33, rele23 activo LOW.')
        config.SERVO_MIN_PULSE_US = ABRIR_US
        pump = PumpRelay()
        servo = ServoSG90()
        control = ControlManual(pump, servo)
        poll = select.poll()
        poll.register(sys.stdin, select.POLLIN)
        print('\nPETCARE', VERSION)
        print('Inicio: rele apagado, servo sin PWM. Sin red, sensores ni buzzer.')
        print('Servo GPIO33 50 Hz: abrir 850 us / cerrar 1500 us. Rele K1 GPIO23.')
        print('No se permiten bomba y servo con PWM simultaneos.')
        print('Para agua: bomba sumergida, manguera al tazon y espacio suficiente.')
        print('1 Abrir | 2 Cerrar | 3 Agua 3 s | 4 Apagar agua | 5 Detener ambos | 0 Salir')
        print('Escribe opcion + Enter. El reloj sigue corriendo aunque no escribas.')
        line = ''
        while not control.terminado:
            control.tick(time.ticks_ms())
            events = poll.poll(0)
            for event in events:
                if event[1] & (select.POLLERR | select.POLLHUP):
                    raise OSError('Consola desconectada')
            if events:
                char = sys.stdin.read(1)
                if char == '\x03':
                    raise KeyboardInterrupt
                if char in ('\r', '\n'):
                    if line.strip():
                        option, line = line.strip(), ''
                        ok, message = control.comando(option, time.ticks_ms())
                        print('Opcion', option, 'OK' if ok else 'RECHAZADA', '-', message)
                elif char in ('\b', '\x7f'):
                    line = line[:-1]
                elif len(line) < 16:
                    line += char
                else:
                    line = ''
            time.sleep_ms(5)
    except KeyboardInterrupt:
        print('Parada solicitada.')
    except Exception as exc:
        print('Prueba detenida:', repr(exc))
    finally:
        if control:
            try:
                control.detener()
            except Exception as exc:
                print('Error de parada:', repr(exc))
        else:
            for device, method in ((pump, 'off'), (servo, 'release')):
                if device:
                    try:
                        getattr(device, method)()
                    except Exception as exc:
                        print('Error de parada:', repr(exc))
        config.SERVO_MIN_PULSE_US = previous_min
        print('FIN: sin nuevos movimientos. Retirar PWM no desconecta los 5 V.')


if __name__ == '__main__':
    main()
