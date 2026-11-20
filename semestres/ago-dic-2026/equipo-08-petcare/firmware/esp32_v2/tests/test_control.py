import sys,types,time,json,tempfile,unittest,hashlib
from pathlib import Path
ROOT=Path(__file__).parent
FW=ROOT.parent
sys.path.insert(0,str(FW))
clock=[0]
time.ticks_ms=lambda:clock[0]
time.ticks_add=lambda a,b:(a+b)%(1<<30)
time.ticks_diff=lambda a,b:((a-b+(1<<29))%(1<<30))-(1<<29)
time.sleep_us=lambda n:None
time.sleep_ms=lambda n:clock.__setitem__(0,time.ticks_add(clock[0],n))
class Pin:
 IN=0;OUT=1;PULL_UP=2;PULL_DOWN=3
 def __init__(self,n,*args,**kw):self.n=n;self.v=kw.get('value',0);self.writes=[]
 def value(self,v=None):
  if v is not None:self.v=v;self.writes.append(v)
  return self.v
class PWM:
 def __init__(self,pin,**kw):self.pin=pin;self.f=kw['freq'];self.ns=kw.get('duty_ns');self.active=True
 def freq(self,value=None):
  if value is not None:self.f=value
  return self.f
 def duty_u16(self,value):self.duty=value
 def duty_ns(self,n=None):
  if n is not None:self.ns=n
  return self.ns
 def deinit(self):self.active=False
class Timer:
 ONE_SHOT=0
 def __init__(self,n):self.callback=None
 def init(self,**kw):self.callback=kw['callback'];self.period=kw['period']
 def deinit(self):self.callback=None
machine=types.ModuleType('machine')
machine.Pin=Pin;machine.PWM=PWM;machine.Timer=Timer
machine.disable_irq=lambda:0;machine.enable_irq=lambda n:None
sys.modules['machine']=machine
sys.modules['binascii']=__import__('binascii')
import config
from actuadores import ServoSG90,PumpRelay,ActiveBuzzer
from controlador import PetCareController
from calibracion_pesa import cargar
from mqtt_link import packet,take_packet,MQTTLink,string
from hx711 import HX711

class Sensor:
 def __init__(self):self.g=0;self.valid=True;self.dht=False
 def read(self,now,slow=True):
  return dict(weight_g=self.g,weight_control_g=self.g,weight_age_ms=0,
              calibrated=True,hx_ok=self.valid,dht_ok=self.dht)

class Tests(unittest.TestCase):
 def setUp(self):
  clock[0]=1000
  self.s=Sensor();self.v=ServoSG90();self.p=PumpRelay();self.b=ActiveBuzzer()
  self.c=PetCareController(self.s,self.v,self.p,self.b);self.c.tick(clock[0])
 def tick(self,ms):clock[0]=time.ticks_add(clock[0],ms);return self.c.tick(clock[0])
 def test_pin_map(self):
  self.assertEqual((config.PIN_SERVO,config.PIN_PUMP_RELAY,config.PIN_BUZZER,config.PIN_DHT22,config.PIN_PIR,config.PIN_HX711_DOUT,config.PIN_HX711_SCK,config.OLED_SDA,config.OLED_SCL),(33,23,22,4,27,19,18,26,25))
 def test_boot_does_not_move(self):self.assertIsNone(self.v.pwm);self.assertEqual(self.p.pin.value(),1)
 def test_servo_exact_pulses_hold(self):
  self.assertTrue(self.c.request_gate(True,1000)[0]);p=self.v.pwm
  self.tick(600);self.assertIs(self.v.pwm,p);self.assertEqual(p.ns,1350000)
  self.c.request_gate(False,1600);self.assertEqual(p.ns,1690000);self.assertTrue(p.active)
 def test_never_800_or_3000(self):
  for x in (800,3000,1390,True):
   with self.assertRaises(ValueError):self.v.move_us(x)
 def test_dry_gate_ignores_bad_scale_and_holds(self):
  self.s.g=1470;self.s.valid=False;self.tick(1)
  self.assertTrue(self.c.command('gate_test_open',1001)[0])
  self.tick(120000);self.assertEqual(self.v.pulse,1350);self.assertTrue(self.c.gate_test_open)
  self.assertFalse(self.c.request_food(clock[0])[0])
  self.assertTrue(self.c.command('gate_close',clock[0])[0])
  self.assertEqual(self.v.pulse,1690);self.assertFalse(self.c.gate_test_open)
 def test_manual_closes_at_300(self):
  self.c.request_gate(True,1000);self.s.g=299;self.tick(10);self.assertEqual(self.v.pulse,1350)
  self.s.g=300;self.tick(10);self.assertEqual(self.v.pulse,1690);self.assertIsNone(self.c.food_mode)
 def test_feed_batch_then_target(self):
  self.assertTrue(self.c.request_food(1000)[0]);self.tick(1);self.assertEqual(self.v.pulse,1350)
  self.tick(250);self.assertEqual(self.v.pulse,1690)
  self.s.g=301;self.tick(1200);self.assertIsNone(self.c.food_mode)
 def test_no_progress_closes(self):
  self.c.request_food(1000)
  for _ in range(12):self.tick(1300)
  self.assertIsNone(self.c.food_mode);self.assertEqual(self.v.pulse,1690)
 def test_sensor_lost_closes(self):
  self.c.request_gate(True,1000);self.s.valid=False;self.tick(10)
  self.assertEqual(self.v.pulse,1690)
 def test_close_works_with_bad_weight(self):
  self.s.valid=False;self.tick(1);self.assertTrue(self.c.request_gate(False,1001)[0])
 def test_bad_weight_no_auto_feed(self):
  self.s.valid=False;self.tick(1);self.assertFalse(self.c.request_food(1001)[0])
 def test_water_exact_deadline(self):
  self.assertTrue(self.c.request_pump(1000)[0]);self.assertEqual(self.p.pin.value(),0)
  self.tick(4999);self.assertTrue(self.p.active)
  self.tick(1);self.assertFalse(self.p.active);self.assertEqual(self.p.pin.value(),1)
  self.assertEqual(self.c.water_events[-1]['duration_ms'],5000)
 def test_timer_independent_cutoff(self):
  self.p.on();self.p.timer.callback(None);self.assertFalse(self.p.active);self.assertEqual(self.p.pin.value(),1)
 def test_water_does_not_move_servo(self):
  self.c.request_gate(False,1000);p=self.v.pwm
  self.c.request_pump(1000);self.tick(5000)
  self.assertIs(self.v.pwm,p);self.assertEqual(p.ns,1690000);self.assertEqual(p.f,50)
 def test_no_overlap_water_food(self):
  self.c.request_gate(True,1000);self.assertFalse(self.c.request_pump(1000)[0])
 def test_buzzer_stops_and_no_pwm_change(self):
  self.v.move_us(1690);self.c.request_beep(1000,'passive')
  self.assertEqual(self.b.pwm.freq(),1000);self.assertEqual(self.v.pwm.freq(),50)
  self.tick(2000);self.assertIsNone(self.b.pwm);self.assertEqual(self.v.pwm.duty_ns(),1690000)
 def test_two_notes_do_not_change_servo(self):
  self.v.move_us(1690);self.c.request_beep(1000,'passive')
  self.tick(700);self.assertEqual(self.b.pwm.duty,0)
  self.tick(200);self.assertEqual(self.b.pwm.freq(),1500);self.assertEqual(self.b.pwm.duty,32768)
  self.assertEqual(self.v.pwm.freq(),50);self.assertEqual(self.v.pulse,1690)
  self.tick(1100);self.assertIsNone(self.b.pwm)
 def test_dht_failure_not_blocks_water(self):
  self.assertFalse(self.c.status['dht_ok']);self.assertTrue(self.c.request_pump(1000)[0])
 def test_shutdown(self):
  self.p.on();self.b.on();self.v.move_us(1690);self.c.safe_shutdown()
  self.assertFalse(self.p.active);self.assertIsNone(self.v.pwm);self.assertEqual(self.b.pin.value(),0)
 def test_saved_calibration_no_mutation(self):
  p=FW/'calibracion_validada.json';before=p.read_bytes()
  for _ in range(5):
   c=cargar(str(FW));self.assertEqual(c['factor'],285.80386);self.assertEqual(c['tara'],-428929.16)
  self.assertEqual(before,p.read_bytes())
 def test_newer_tare_does_not_override(self):
  with tempfile.TemporaryDirectory() as folder:
   Path(folder,'calibracion_validada.json').write_bytes((FW/'calibracion_validada.json').read_bytes())
   Path(folder,'tara_tazon.json').write_text('{"TARE_RAW":0}')
   self.assertEqual(cargar(folder)['tara'],-428929.16)
 def test_missing_calibration_not_zero(self):
  with tempfile.TemporaryDirectory() as folder:
   c=cargar(folder);self.assertIsNone(c['factor']);self.assertIsNotNone(c['error'])
 def test_mqtt_partial_packet_nonblocking(self):
  p=packet(0x30,b'a'*300);b=bytearray()
  for v in p[:-1]:b.append(v);self.assertIsNone(take_packet(b))
  b.append(p[-1]);self.assertEqual(take_packet(b),(0x30,b'a'*300,len(p)))
 def test_mqtt_bad_length(self):
  with self.assertRaises(ValueError):take_packet(bytearray(b'\x30\xff\xff\xff\xff'))
 def test_mqtt_retained_command_ignored(self):
  m=MQTTLink();m.receive(0x31,string(m.base+'/commands')+json.dumps({'id':'1','action':'gate_close','session_id':self.c.session}).encode(),self.c,1000)
  self.assertIsNone(self.v.pwm)
 def test_mqtt_duplicate_not_reexecuted(self):
  m=MQTTLink();d={'id':'1','action':'water','supervised':True,'session_id':self.c.session}
  body=string(m.base+'/commands')+json.dumps(d).encode()
  m.receive(0x30,body,self.c,1000);m.receive(0x30,body,self.c,1000)
  self.assertEqual(self.c.water_sequence,1)
 def test_ticks_wrap(self):
  clock[0]=(1<<30)-2000;self.c.request_pump(clock[0]);self.tick(5000)
  self.assertFalse(self.p.active);self.assertEqual(self.c.water_events[-1]['duration_ms'],5000)
 def test_hx_signed_and_25_clocks(self):
  h=HX711(19,18);clock[0]+=500
  bits=[0]+[(0xffff9c>>i)&1 for i in range(23,-1,-1)]
  h.dout.value=lambda:bits.pop(0)
  h.sck.writes=[]
  self.assertEqual(h.read_ready(),-100)
  self.assertEqual(sum(h.sck.writes),25);self.assertEqual(h.sck.value(),0)

if __name__=='__main__':unittest.main(verbosity=2)
