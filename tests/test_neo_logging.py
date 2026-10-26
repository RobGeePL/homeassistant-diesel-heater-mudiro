"""Neo log confidentiality with synthetic credentials and an offline BLE double."""
import asyncio
import datetime
import logging
import time
import types
import unittest
from unittest.mock import Mock

import test_offline
from test_offline import method


class BleakError(Exception):
    """Offline substitute; no BLE or Home Assistant imports."""


PASSWORD = 123456789  # Synthetic fixture, never a device credential.
# Captured from the unmodified method at 2026-01-01 00:00:00 UTC.
AUTH = bytes.fromhex('290d5c006955b900075bcd15011165')
ACK = bytearray(b'\x5c\x16' + bytes(22))
LEAK = f'{PASSWORD} {PASSWORD:08x} {AUTH.hex()} {AUTH!r} {bytearray(AUTH)!r}'


class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def text(self):
        formatter = logging.Formatter('%(levelname)s %(message)s')
        return '\n'.join(formatter.format(r) + repr(r.args) for r in self.records)


class NeoLogging(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.log = logging.Logger('neo-offline', logging.DEBUG)
        self.capture = Capture()
        self.log.addHandler(self.capture)

    def host(self):
        h = test_offline.Offline().host()
        h._logger = self.log
        h._neo_password = PASSWORD
        h._is_hcalory_device = False
        h._is_abba_device = True
        h._abba_write_char = types.SimpleNamespace(uuid='0000fff1-offline')
        h._characteristic = types.SimpleNamespace(uuid='0000fff2-offline', properties=['notify'])
        h._active_char_uuid = h._characteristic.uuid
        h._protocol_mode = 5
        h._protocol = None
        h._write_gatt = types.MethodType(method(
            'coordinator.py', 'VevorHeaterCoordinator', '_write_gatt', {'BleakError': BleakError}), h)
        self.calls = []

        async def write(char, packet, *, response):
            self.calls.append((char, bytes(packet), response))
            h._notification_data = ACK.copy()

        h._client.write_gatt_char = write
        return h

    def auth(self, ticks=None):
        async def sleep(_):
            pass
        return method('coordinator.py', 'VevorHeaterCoordinator', '_send_dz06_neo_auth', {
            'asyncio': types.SimpleNamespace(sleep=sleep),
            'time': time if ticks is None else types.SimpleNamespace(monotonic=lambda: next(ticks)),
            'timedelta': datetime.timedelta,
            'dt_util': types.SimpleNamespace(now=lambda: datetime.datetime(
                2026, 1, 1, tzinfo=datetime.timezone.utc))})

    def assert_safe(self):
        text = self.capture.text()
        for secret in (str(PASSWORD), f'{PASSWORD:08x}', AUTH.hex(), repr(AUTH), repr(bytearray(AUTH))):
            self.assertNotIn(secret, text)
        return text

    async def test_auth_bytes_and_success_at_every_log_threshold(self):
        for level in (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL):
            with self.subTest(level=level):
                self.log.setLevel(level)
                self.capture.records.clear()
                h = self.host()
                self.assertTrue(await self.auth()(h))
                self.assertEqual(self.calls, [(h._abba_write_char, AUTH, False)])
                text = self.assert_safe()
                if level <= logging.INFO:
                    self.assertIn('Starting DZ06 Neo authorization', text)
                    self.assertIn('authorization succeeded', text)
                    self.assertIn('Sent 15 bytes', text)
                if level == logging.DEBUG:
                    self.assertIn('Waiting up to 10s', text)

    async def test_auth_timeout_and_invalid_config(self):
        h = self.host()
        async def no_ack(char, packet, *, response):
            self.calls.append((char, bytes(packet), response))
        h._client.write_gatt_char = no_ack
        # Same 10-second deadline, advanced without any real wait.
        self.assertFalse(await self.auth(iter([0, 0, 11]))(h))
        self.assertEqual(self.calls, [(h._abba_write_char, AUTH, False)])
        self.assertIn('timed out after 10s', self.assert_safe())
        for invalid in (None, 'invalid', -1, 0x80000000):
            h._neo_password = invalid
            self.assertFalse(await self.auth()(h))
        self.assertEqual(len(self.calls), 1)
        self.assertIn('invalid password configuration', self.assert_safe())

    async def test_backend_exception_and_traceback_are_safe(self):
        h = self.host()
        async def fail(char, packet, *, response):
            self.calls.append((char, bytes(packet), response))
            raise RuntimeError(LEAK)
        h._client.write_gatt_char = fail
        try:
            await self.auth()(h)
        except BleakError as err:
            self.assertIn('RuntimeError', str(err))
            # Model a downstream HA logger, including its rendered traceback.
            self.log.error('Failed to connect: %s', err, exc_info=True)
        else:
            self.fail('Transport failure must still propagate')
        self.assertEqual(self.calls, [(h._abba_write_char, AUTH, False)])
        self.assertIn('authorization write failed', self.assert_safe())

    async def test_disconnect_during_write_and_auth_without_transport_state(self):
        h = self.host()
        async def disconnect(char, packet, *, response):
            h.is_dz06_neo = False
        h._client.write_gatt_char = disconnect
        await h._write_gatt(bytearray(AUTH))
        self.assertIn('payload omitted', self.assert_safe())
        self.capture.records.clear()
        await h._write_gatt(bytearray(AUTH))
        self.assertIn('payload omitted', self.assert_safe())

    async def test_neo_command_errors_only_log_exception_type(self):
        for name, args in (
            ('_async_set_dz06_neo_level', (1,)),
            ('_async_set_dz06_neo_control', (1, 8, 100)),
            ('_send_dz06_neo_power', (True,)),
            ('_send_command', (1, 0)),
        ):
            with self.subTest(method=name):
                h = self.host()
                h.data.update(neo_raw_state=2, neo_run_type=1, set_temp=8,
                              altitude=100, neo_min_target=8, neo_max_target=36)
                async def fail(packet):
                    raise RuntimeError(LEAK)
                h._write_gatt = fail
                f = method('coordinator.py', 'VevorHeaterCoordinator', name)
                self.assertFalse(await f(h, *args))
                self.assertIn('RuntimeError', self.assert_safe())

    async def test_cleanup_errors_are_safe_and_operations_preserved(self):
        h = self.host()
        calls = []
        async def stop(uuid):
            calls.append(('stop', uuid))
            raise RuntimeError(LEAK)
        async def disconnect():
            calls.append(('disconnect',))
            raise RuntimeError(LEAK)
        h._client.stop_notify = stop
        h._client.disconnect = disconnect
        f = method('coordinator.py', 'VevorHeaterCoordinator', '_cleanup_connection')
        await f(h)
        self.assertEqual(calls, [('stop', '0000fff2-offline'), ('disconnect',)])
        self.assertIsNone(h._client)
        self.assertIsNone(h._characteristic)
        self.assertIsNone(h._active_char_uuid)
        self.assertFalse(h._v21_handshake_sent)
        self.assertFalse(h._time_synced_this_session)
        self.assertIn('RuntimeError', self.assert_safe())

    async def test_late_neo_frames_redacted_without_changing_parser_call(self):
        h = self.host()
        h.is_dz06_neo = False
        h._parse_response = Mock(side_effect=RuntimeError(LEAK))
        f = method('coordinator.py', 'VevorHeaterCoordinator', '_notification_callback')
        for frame in (bytearray(AUTH), ACK.copy(), bytearray(b'\x5a\x25' + bytes(37))):
            f(h, 0, frame)
            h._parse_response.assert_called_with(frame)
        self.assertIn('payload omitted', self.assert_safe())
        self.assertIn('Error parsing notification: RuntimeError', self.assert_safe())

    async def test_non_neo_write_and_error_semantics_preserved(self):
        h = self.host()
        h.is_dz06_neo = False
        h._is_abba_device = False
        h._is_hcalory_device = True
        h._hcalory_write_char = types.SimpleNamespace(uuid='offline-bdf7')
        packet = bytearray(b'\xaa\x55\x01\x02')
        await h._write_gatt(packet)
        self.assertEqual(self.calls, [(h._hcalory_write_char, bytes(packet), False)])
        self.assertIn('Hcalory', self.capture.text())
        original = RuntimeError('offline failure')
        async def fail(*args, **kwargs):
            raise original
        h._client.write_gatt_char = fail
        with self.assertRaises(RuntimeError) as raised:
            await h._write_gatt(packet)
        self.assertIs(raised.exception, original)

    async def test_async_cancellation_still_propagates(self):
        h = self.host()
        async def cancelled(*args, **kwargs):
            raise asyncio.CancelledError()
        h._client.write_gatt_char = cancelled
        with self.assertRaises(asyncio.CancelledError):
            await self.auth()(h)


if __name__ == '__main__':
    unittest.main()
