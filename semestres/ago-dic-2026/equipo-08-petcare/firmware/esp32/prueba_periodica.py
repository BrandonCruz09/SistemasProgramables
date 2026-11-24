"""Tres ciclos supervisados. No modifica el modo normal al reiniciar."""
# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Documentar el uso de prueba periodica dentro del proyecto PetCare.

import config


class PruebaPeriodica:
    def __init__(self, controller, now_ms):
        self.controller = controller
        if not getattr(config, 'SERVO_MOVEMENT_ENABLED', True):
            raise ValueError('Compuerta bloqueada: falta confirmar la apertura')
        status = controller.snapshot()
        if not status.get('hx_ok') or not status.get('calibrated'):
            raise ValueError('La prueba requiere lectura valida de la pesa')
        if status.get('weight_g') is None or abs(status['weight_g']) > 3:
            raise ValueError('El tazon vacio no marca cero: revisar tara antes de la prueba')
        self.next_cycle = controller._add(now_ms, 30000)
        self.water_at = None
        self.count = 0
        self.phase = 'espera'
        print('PRUEBA: primer ciclo en 30 s; tres ciclos; agua 3 s por ciclo.')

    def tick(self, now_ms):
        c = self.controller
        if self.phase in ('terminada', 'error'):
            return
        if self.phase == 'espera' and c._diff(now_ms, self.next_cycle) >= 0:
            ok, message = c.request_feed(now_ms)
            print('PRUEBA COMPUERTA:', message)
            if not ok:
                self.phase = 'error'
                c.stop_pump(now_ms)
                return
            self.count += 1
            self.water_at = c._add(now_ms, 3000)
            # No acumular ciclos perdidos si la PC o la red se retrasan.
            self.next_cycle = c._add(now_ms, 30000)
            self.phase = 'cierre'
        elif self.phase == 'cierre' and c.state == c.IDLE and c._diff(now_ms, self.water_at) >= 0:
            if not c.last_event.startswith('Racion terminada'):
                print('PRUEBA detenida: no se completo el cierre por software.')
                self.phase = 'error'
                c.stop_pump(now_ms)
                return
            ok, message = c.request_pump(now_ms, source='prueba_periodica_3s', test=True)
            print('PRUEBA AGUA:', message)
            self.phase = 'agua' if ok else 'error'
        elif self.phase == 'agua' and c.state == c.IDLE:
            if c.last_event != 'Agua: tiempo_cumplido':
                print('PRUEBA interrumpida; no se repetiran los servidos.')
                self.phase = 'error'
                return
            print('PRUEBA: ciclo', self.count, 'terminado; bomba apagada.')
            self.phase = 'terminada' if self.count >= 3 else 'espera'
            if self.phase == 'terminada':
                print('PRUEBA FINALIZADA: sensores siguen; no se repetiran los servidos.')


class BuzzerOmitido:
    def on(self): pass
    def off(self): pass
