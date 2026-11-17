# PetCare: ejecuta el programa completo en modo de prueba supervisada.
# Sin ESP32-CAM ni buzzer. Tres ciclos, separados por 30 segundos.
import config
if not config.SERVO_MOVEMENT_ENABLED:
    raise ValueError('Prueba pausada tras temblor del servo. Revalidar montaje antes de habilitar ciclos.')
if (config.SERVO_OPEN_US, config.SERVO_CLOSED_US) != (1550, 1690):
    raise ValueError('Carga config.py con apertura 1550 y cierre 1690 antes de probar.')
print('PETCARE - PRUEBA INTEGRADA')
print('Compuerta: abrir 1550 us; cerrar 1690 us.')
print('Tazon de comida VACIO y sin croquetas. No tocarlo durante la lectura.')
print('Bomba sumergida, manguera al tazon de agua y espacio para tres pulsos de 3 s.')
print('Primer ciclo 30 s despues de arrancar; despues tres ciclos en total.')
print('Stop o Ctrl+C interrumpe. Si la compuerta fuerza su apoyo, apaga la fuente.')
if input('Con la fuente encendida y todo listo, escribe LISTO y Enter: ').strip().upper() == 'LISTO':
    from main import main
    main(prueba_periodica=True)
else:
    print('Prueba cancelada sin mover actuadores.')
