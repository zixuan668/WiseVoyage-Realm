"""Status reports the deployed cloud paths without contacting providers or PostgreSQL."""
import asyncio
import os
import unittest
from unittest.mock import MagicMock, patch

from server.base.base_server import system_status
from server.base.database import init_db
from server.base.server_info import ServerPluginsInfo, SERVER_PLUGINS_INFO


class SystemStatusTests(unittest.TestCase):
    def test_cloud_configuration_does_not_probe_retired_local_workers(self):
        info = ServerPluginsInfo()
        with patch.dict(os.environ, {'LLM_API_KEY': 'unit-test-key', 'DASHSCOPE_API_KEY': 'unit-test-key'}), \
             patch.object(info, '_check_server', return_value=False) as probe, \
             patch('server.base.server_info.find_spec', return_value=object()):
            info.update_info()
        self.assertTrue(info.llm_enabled)
        self.assertTrue(info.asr_server_enabled)
        self.assertTrue(info.tts_server_enabled)
        self.assertFalse(info.digital_human_server_enabled)
        self.assertEqual(probe.call_count, 1)
        self.assertIn(':8002/', probe.call_args.args[0])

    def test_status_distinguishes_configured_cloud_from_ready_local_worker(self):
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value.execute.return_value.scalar.return_value = True
        with patch.object(init_db, 'DB_ENGINE', engine), \
             patch.object(SERVER_PLUGINS_INFO, 'update_info'), \
             patch.object(SERVER_PLUGINS_INFO, 'tts_server_enabled', True), \
             patch.object(SERVER_PLUGINS_INFO, 'digital_human_server_enabled', False), \
             patch.dict(os.environ, {'LLM_API_KEY': 'unit-test-key', 'DASHSCOPE_API_KEY': 'unit-test-key'}):
            result = asyncio.run(system_status())
        self.assertEqual(result['llm']['status'], 'configured')
        self.assertEqual(result['asr']['status'], 'configured')
        self.assertIn('qwen3-asr-flash', result['asr']['engine'])
        self.assertEqual(result['tts']['status'], 'configured')
        self.assertEqual(result['digital_human']['status'], 'configured')
        self.assertTrue(result['digital_human']['xingyun_configured'])
        self.assertFalse(result['digital_human']['musetalk_available'])
        self.assertNotIn('unit-test-key', str(result))

    def test_placeholder_keys_do_not_claim_cloud_configuration(self):
        info = ServerPluginsInfo()
        with patch.dict(os.environ, {'LLM_API_KEY': 'local-demo-disabled', 'DASHSCOPE_API_KEY': ''}), \
             patch.object(info, '_check_server', return_value=False):
            info.update_info()
        self.assertFalse(info.llm_enabled)
        self.assertFalse(info.asr_server_enabled)
