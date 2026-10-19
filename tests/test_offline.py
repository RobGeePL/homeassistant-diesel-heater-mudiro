"""Offline regression tests: real method bodies, synthetic frames, no HA/BLE."""
import ast
import asyncio
import json
import logging
import pathlib
import types
import unittest
from unittest.mock import AsyncMock

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMP = ROOT / 'custom_components/diesel_heater'


def method(file, cls, name, env=None):
    tree = ast.parse((COMP / file).read_text())
    owner = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
    node = next(n for n in owner.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    node.decorator_list = []
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), node], type_ignores=[])
    scope = dict(env or {})
    exec(compile(ast.fix_missing_locations(module), file, 'exec'), scope)
    return scope[name]


class Offline(unittest.TestCase):
    def host(self):
        h = types.SimpleNamespace(is_dz06_neo=True, data={}, _logger=logging.getLogger('test'), _notification_data=None,
                                  _burnoff=types.SimpleNamespace(observe_status=lambda: None, schedule_abort_if_ecu_stopped=lambda: None))
        for name in ['_neo_packet', '_neo_control_settings']:
            f = method('coordinator.py', 'VevorHeaterCoordinator', name)
            setattr(h, name, f if name == '_neo_packet' else types.MethodType(f, h))
        h._client = types.SimpleNamespace(is_connected=True)
        h.async_request_refresh = AsyncMock()
        return h

    def test_layout_and_json(self):
        self.assertEqual([p.name for p in (ROOT/'custom_components').iterdir()], ['diesel_heater'])
        for p in ROOT.rglob('*.json'):
            json.loads(p.read_text())
        m = json.loads((COMP/'manifest.json').read_text())
        self.assertEqual(m['requirements'], ['diesel-heater-ble==0.3.8'])
        self.assertTrue(m['config_flow'])
        self.assertEqual(m['domain'], 'diesel_heater')
        for key in ['name','documentation','issue_tracker','codeowners','version']:
            self.assertTrue(m[key])
        self.assertTrue((COMP/'brand/icon.png').is_file())
        self.assertEqual((COMP/'strings.json').read_bytes(), (COMP/'translations/en.json').read_bytes())

    def test_syntax(self):
        for p in ROOT.rglob('*.py'):
            compile(p.read_text(), str(p), 'exec')

    def test_unknown_settings_and_defaults(self):
        h = self.host()
        self.assertIsNone(h._neo_control_settings())
        self.assertEqual(h._neo_control_settings(True), (1, 8, 1))
        h.data.update(neo_raw_state=0, neo_run_type=None, set_temp=None, altitude=None)
        self.assertIsNone(h._neo_control_settings())

    def test_status_decoding(self):
        f = method('coordinator.py', 'VevorHeaterCoordinator', '_notification_callback', {
            'RUNNING_STATE_ON':1, 'RUNNING_STATE_OFF':0, 'RUNNING_STEP_RUNNING':2,
            'RUNNING_STEP_COOLDOWN':3, 'RUNNING_STEP_STANDBY':0, 'RUNNING_MODE_LEVEL':1,
            'RUNNING_MODE_TEMPERATURE':2})
        h = self.host()
        b = bytearray(39); b[:2] = b'\x5a\x25'; b[3]=2; b[4]=4
        b[5:7]=(126).to_bytes(2,'big'); b[7:9]=(3200).to_bytes(2,'big')
        b[13:15]=(23).to_bytes(2,'big'); b[15]=35; b[16]=8; b[17]=9
        b[18:20]=(250).to_bytes(2,'big',signed=True); b[26]=7; b[34]=1; b[35]=251
        f(h, 0, b)
        for k,v in {'supply_voltage':12.6,'cab_temperature':-5.0,'set_level':10,'error_code':3,
                    'neo_fire_temperature':250,'neo_fan_speed_raw':3200,'neo_frequency_raw':8,
                    'neo_fuel_raw':9,'neo_remaining_time_raw':7,'neo_igniter_current_raw':23}.items():
            self.assertEqual(h.data[k],v,k)
        b[34]=2; f(h,0,b); self.assertIsNone(h.data['set_level'])
        c=bytearray(24); c[:2]=b'\x5c\x16'; c[4]=8;c[5]=36; f(h,0,c)
        self.assertEqual(h.data['neo_min_target'],8)
        before=dict(h.data); f(h,0,bytearray(12)); self.assertEqual(before,h.data)

    def test_problem_and_error_unknown(self):
        tree=ast.parse((COMP/'binary_sensor.py').read_text())
        cls=next(c.name for c in tree.body if isinstance(c,ast.ClassDef) and any(isinstance(n,ast.FunctionDef) and n.name=='is_on' and 'neo_error_raw' in ast.unparse(n) for n in c.body))
        f=method('binary_sensor.py',cls,'is_on',{'ERROR_NONE':0})
        h=types.SimpleNamespace(coordinator=self.host())
        self.assertIsNone(f(h))
        for raw in [0,1,4,255]:
            h.coordinator.data['neo_error_raw']=raw
            self.assertEqual(f(h),raw!=0)
        tree=ast.parse((COMP/'sensor.py').read_text())
        cls=next(c.name for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='VevorErrorCodeSensor')
        f=method('sensor.py',cls,'native_value',{'NEO_ERROR_NAMES':{0:'No fault',3:'Glow plug fault'}})
        h.coordinator.data={}; self.assertIsNone(f(h))
        h.coordinator.data={'neo_error_raw':4,'error_code':3}; self.assertEqual(f(h),'Glow plug fault')
        h.coordinator.data={'neo_error_raw':255,'error_code':254}; self.assertIn('Unknown Neo error',f(h))

    def test_fan_none(self):
        tree=ast.parse((COMP/'fan.py').read_text())
        cls=next(c.name for c in tree.body if isinstance(c,ast.ClassDef))
        f=method('fan.py',cls,'percentage')
        self.assertIsNone(f(types.SimpleNamespace(coordinator=types.SimpleNamespace(data={'set_level':None}))))


class Commands(unittest.IsolatedAsyncioTestCase):
    async def test_authentication(self):
        import datetime
        f=method('coordinator.py','VevorHeaterCoordinator','_send_dz06_neo_auth',{
            'asyncio':asyncio,'time':__import__('time'),'timedelta':datetime.timedelta,
            'dt_util':types.SimpleNamespace(now=lambda:datetime.datetime(2026,1,1,tzinfo=datetime.timezone.utc))})
        h=Offline().host();h._neo_password=100000000;packets=[]
        async def write(packet):
            packets.append(packet);h._notification_data=bytearray(b'\x5c\x16'+bytes(22))
        h._write_gatt=write
        self.assertTrue(await f(h));self.assertEqual(packets[0][:3],b'\x29\x0d\x5c')
        self.assertEqual(int.from_bytes(packets[0][8:12],'big'),100000000)
        h._neo_password=None;self.assertFalse(await f(h));self.assertEqual(len(packets),1)

    async def test_wrong_level_confirmation_rejected(self):
        ticks=iter([0,0,4])
        async def sleep(_):pass
        f=method('coordinator.py','VevorHeaterCoordinator','_async_set_dz06_neo_level',{
            'asyncio':types.SimpleNamespace(sleep=sleep),'time':types.SimpleNamespace(monotonic=lambda:next(ticks))})
        h=Offline().host();h.data.update(neo_raw_state=2,neo_run_type=1,set_temp=8,altitude=100,neo_min_target=8,neo_max_target=36)
        async def write(packet):
            b=bytearray(39);b[:2]=b'\x5a\x25';b[15]=35;b[34]=1;b[32:34]=(100).to_bytes(2,'big');h._notification_data=b
        h._write_gatt=write
        self.assertFalse(await f(h,1));h.async_request_refresh.assert_not_awaited()

    async def test_aa55_routing(self):
        class CBFF:
            def is_feaa_frame(self,data):return False
        g={'ProtocolCBFF':CBFF,'PROTOCOL_HEADER_CBFF':0xcbff,'PROTOCOL_HEADER_ABBA':0xabba}
        f=method('coordinator.py','VevorHeaterCoordinator','_detect_protocol',g)
        h=types.SimpleNamespace(_is_hcalory_device=False,_is_abba_device=False,_protocol_mode=0,
                                _protocols={1:'AA55',3:'AA66',6:CBFF()})
        for length in [18,20]:
            b=bytearray(b'\xaa\x55'+bytes(length-2))
            self.assertEqual(f(h,b,0xaa55),('AA55',b))
        b=bytearray(b'\xaa\x66'+bytes(18));self.assertEqual(f(h,b,0xaa66),('AA66',b))

    async def test_level_confirmation_and_limits(self):
        for level in range(1,11):
            h=Offline().host(); h.data.update(neo_raw_state=2,neo_run_type=1,set_temp=8,altitude=100,neo_min_target=8,neo_max_target=36)
            captured=[]
            async def write(packet):
                captured.append(packet)
                b=bytearray(39);b[:2]=b'\x5a\x25';b[15]=8+3*(level-1);b[34]=1;b[32:34]=(100).to_bytes(2,'big');h._notification_data=b
            h._write_gatt=write
            f=method('coordinator.py','VevorHeaterCoordinator','_async_set_dz06_neo_level',{'asyncio':asyncio,'time':__import__('time')})
            self.assertTrue(await f(h,level));self.assertEqual(captured[0][3],0x51)
            crc=0xffff
            for byte in captured[0][:-2]:
                crc^=byte
                for _ in range(8):crc=(crc>>1)^0xa001 if crc&1 else crc>>1
            self.assertEqual(captured[0][-2:],crc.to_bytes(2,'big'))
            for invalid in [None,True,0,11,1.5]:
                with self.assertRaises(ValueError):await f(h,invalid)
            h.data['neo_min_target']=None;self.assertFalse(await f(h,level))

    async def test_power_confirmation(self):
        f=method('coordinator.py','VevorHeaterCoordinator','_send_dz06_neo_power',{'asyncio':asyncio,'time':__import__('time')})
        for on in [False,True]:
            h=Offline().host();h.data.update(neo_raw_state=0,neo_run_type=1,set_temp=8,altitude=0)
            captured=[]
            async def write(packet):
                captured.append(packet);b=bytearray(39);b[:2]=b'\x5a\x25';b[3]=2 if on else 0;h._notification_data=b
            h._write_gatt=write
            self.assertTrue(await f(h,on));self.assertEqual(captured[0][3],0x5a if on else 0x5c)

    async def test_late_entities_no_duplicates(self):
        tree=ast.parse((COMP/'sensor.py').read_text())
        setup=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='async_setup_entry')
        start=next(i for i,n in enumerate(setup.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='neo_entities_added' for t in n.targets))
        tail=ast.AsyncFunctionDef(name='setup',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=x) for x in ['coordinator','entry','async_add_entities']],kwonlyargs=[],kw_defaults=[],defaults=[]),body=setup.body[start:],decorator_list=[])
        g={'callback':lambda f:f}
        for name in ['NeoFireTemperatureSensor','NeoFanSpeedRawSensor','NeoRawDiagnosticSensor']:g[name]=lambda *args:args
        exec(compile(ast.fix_missing_locations(ast.Module(body=[tail],type_ignores=[])),'late_entities','exec'),g)
        listeners=[]; batches=[]
        h=types.SimpleNamespace(is_dz06_neo=False,async_add_listener=lambda f:listeners.append(f))
        await g['setup'](h,types.SimpleNamespace(async_on_unload=lambda f:None),batches.append)
        self.assertEqual(batches,[])
        h.is_dz06_neo=True
        listeners[0]();listeners[0]();h.is_dz06_neo=False;listeners[0]();h.is_dz06_neo=True;listeners[0]()
        self.assertEqual(len(batches),1);self.assertEqual(len(batches[0]),6)


if __name__=='__main__':unittest.main()
