"""Exercise the actual request functions with SDK clients mocked; no keys or network required."""
import ast
import asyncio
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def response(content='Verified guide answer.'):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class LlmRequestTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        source = Path(__file__).parents[2] / 'server/base/routers/llm.py'
        functions = [node for node in ast.parse(source.read_text(encoding='utf-8')).body
                     if isinstance(node, ast.AsyncFunctionDef) and node.name in ('get_llm_res', 'get_tour_llm_res')]
        self.handler = MagicMock()
        self.primary = self.handler.with_options.return_value
        self.primary.chat.completions.create.return_value = response()
        self.scope = {'os': os, 'logger': MagicMock(), 'LLM_MODEL_HANDLER': self.handler}
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), self.scope)
        self.environment = patch.dict(os.environ, {'LLM_MODEL_NAME': 'primary-test', 'TOUR_LLM_USE_VISION_PROVIDER': 'false'})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    async def test_normal_request_reaches_configured_sdk_without_name_error(self):
        answer = await self.scope['get_llm_res']([{'role': 'user', 'content': 'Hello'}], timeout=12)
        self.assertEqual(answer, 'Verified guide answer.')
        self.handler.with_options.assert_called_once_with(timeout=12, max_retries=0)
        self.assertEqual(self.primary.chat.completions.create.call_args.kwargs['model'], 'primary-test')

    async def test_optional_provider_does_not_affect_general_requests(self):
        with patch.dict(os.environ, {'TOUR_LLM_USE_VISION_PROVIDER': 'true'}), patch('openai.OpenAI') as constructor:
            await self.scope['get_llm_res']([])
        constructor.assert_not_called()
        self.primary.chat.completions.create.assert_called_once()

    async def test_tour_wrapper_selects_and_closes_optional_client(self):
        owned = MagicMock()
        owned.chat.completions.create.return_value = response('Tour provider answer.')
        settings = {'TOUR_LLM_USE_VISION_PROVIDER': 'true', 'VISION_API_KEY': 'unit-test-key',
                    'VISION_API_BASE': 'https://example.invalid/v1', 'VISION_MODEL': 'tour-test'}
        with patch.dict(os.environ, settings), patch('openai.OpenAI', return_value=owned), patch('httpx.Client'):
            answer = await self.scope['get_tour_llm_res']([], timeout=15)
        self.assertEqual(answer, 'Tour provider answer.')
        self.assertEqual(owned.chat.completions.create.call_args.kwargs['model'], 'tour-test')
        self.primary.chat.completions.create.assert_not_called()
        owned.close.assert_called_once()

    async def test_json_fallback_uses_same_selected_provider(self):
        owned = MagicMock()
        owned.chat.completions.create.side_effect = [RuntimeError('format not supported'), response('{"ok":true}')]
        settings = {'TOUR_LLM_USE_VISION_PROVIDER': 'true', 'VISION_API_KEY': 'unit-test-key',
                    'VISION_API_BASE': 'https://example.invalid/v1', 'VISION_MODEL': 'tour-test'}
        with patch.dict(os.environ, settings), patch('openai.OpenAI', return_value=owned), patch('httpx.Client'):
            answer = await self.scope['get_tour_llm_res']([], json_mode=True)
        self.assertEqual(answer, '{"ok":true}')
        calls = owned.chat.completions.create.call_args_list
        self.assertEqual(calls[0].kwargs['response_format'], {'type': 'json_object'})
        self.assertNotIn('response_format', calls[1].kwargs)
        self.assertTrue(all(call.kwargs['model'] == 'tour-test' for call in calls))
        self.primary.chat.completions.create.assert_not_called()
        owned.close.assert_called_once()

    async def test_owned_client_is_closed_even_when_request_fails(self):
        owned = MagicMock()
        owned.chat.completions.create.side_effect = TimeoutError()
        settings = {'TOUR_LLM_USE_VISION_PROVIDER': 'true', 'VISION_API_KEY': 'unit-test-key',
                    'VISION_API_BASE': 'https://example.invalid/v1'}
        with patch.dict(os.environ, settings), patch('openai.OpenAI', return_value=owned), patch('httpx.Client'):
            with self.assertRaises(TimeoutError):
                await self.scope['get_tour_llm_res']([])
        owned.close.assert_called_once()

    async def test_empty_model_content_is_an_explicit_error(self):
        self.primary.chat.completions.create.return_value = response('  ')
        with self.assertRaises(RuntimeError):
            await self.scope['get_llm_res']([])

    async def test_tour_request_has_an_outer_deadline_even_if_provider_stalls(self):
        cancelled=asyncio.Event()
        async def stalled(*args, **kwargs):
            try: await asyncio.sleep(30)
            finally: cancelled.set()
        self.scope['get_llm_res']=stalled
        with self.assertRaises(TimeoutError):
            await self.scope['get_tour_llm_res']([],timeout=.01)
        self.assertTrue(cancelled.is_set())


if __name__ == '__main__':
    unittest.main()
