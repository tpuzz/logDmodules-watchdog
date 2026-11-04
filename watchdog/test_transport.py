"""Nonmathematical transport, deduplication and race regression tests."""
import base64
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock
from supervisor import emit_diagnostic, emit_recovery, decide, TEST_FIXTURE_ID
import test_logdmodules
from event_policy import classify_event


class DiagnosticTransportTests(unittest.TestCase):
    def setUp(self):
        self.identity = 'logdmodules-supervisor-e2e-unit-test'
        self.snapshot = ('test-commit', {'status': 'running'}, {'status': 'active'})
        self.fixture = (Path(__file__).parent / 'test-fixture.json').read_bytes()
        self.test_owner = dict(fixture_id=TEST_FIXTURE_ID, test_only=True,
                               status='released', owner_run_id=None)
        self.api = Mock(repo='tpuzz/logDmodules-watchdog')
        self.api.snapshot.return_value = self.snapshot
        self.calls, self.marker = [], None
        self.api.file.side_effect = lambda path, ref: self.test_owner if path.endswith('test-owner.json') else self.marker
        self.api.request.side_effect = self.request

    def request(self, method, endpoint, payload=None, **kwargs):
        self.calls.append((method, endpoint, payload))
        if method == 'GET' and endpoint.startswith('/contents/watchdog/test-fixture.json?'):
            return {'content': base64.b64encode(self.fixture).decode()}
        if method == 'GET' and endpoint.startswith('/pulls?'): return []
        if method == 'GET' and endpoint.startswith('/git/ref/'): return None
        if method == 'GET' and endpoint.startswith('/git/commits/'): return {'tree': {'sha': 'tree'}}
        if method == 'POST' and endpoint == '/git/trees':
            self.marker = json.loads(payload['tree'][0]['content'])
            return {'sha': 'new-tree'}
        if method == 'POST' and endpoint == '/git/commits': return {'sha': 'new-commit'}
        if method == 'POST' and endpoint == '/git/refs': return {}
        if method == 'POST' and endpoint == '/pulls':
            return {'html_url': 'https://github.com/tpuzz/logDmodules-watchdog/pull/999', **payload}
        raise AssertionError((method, endpoint))

    def test_transport_is_distinct_from_live_production(self):
        result = emit_diagnostic(self.api, self.identity)
        self.assertTrue(result['title'].startswith('LOGDMODULES_RECOVERY_TEST NON-MATHEMATICAL '))
        self.assertTrue(self.marker['test_only'])
        self.assertFalse(self.marker['mathematics_authorized'])
        self.assertEqual(self.marker['fixture_id'], TEST_FIXTURE_ID)
        self.assertFalse(any(method in ('PUT', 'DELETE', 'PATCH') for method, _, _ in self.calls))
        writes = [p for method, endpoint, p in self.calls if endpoint == '/git/trees']
        self.assertEqual(len(writes[0]['tree']), 1)
        self.assertTrue(writes[0]['tree'][0]['path'].startswith('watchdog/events/'))

    def test_fixture_hash_mismatch_prevents_mutation(self):
        self.fixture += b' '
        with self.assertRaises(ValueError): emit_diagnostic(self.api, self.identity)
        self.assertFalse(any(method != 'GET' for method, _, _ in self.calls))

    def test_active_test_owner_prevents_mutation(self):
        self.test_owner.update(status='active', owner_run_id='another-execution')
        with self.assertRaises(ValueError): emit_diagnostic(self.api, self.identity)
        self.assertFalse(any(method != 'GET' for method, _, _ in self.calls))

    def test_racing_test_owner_prevents_pr(self):
        original = self.request
        def race(method, endpoint, payload=None, **kwargs):
            result = original(method, endpoint, payload, **kwargs)
            if method == 'POST' and endpoint == '/git/refs':
                self.test_owner.update(status='active', owner_run_id='another-execution')
            return result
        self.api.request.side_effect = race
        with self.assertRaises(ValueError): emit_diagnostic(self.api, self.identity)
        self.assertFalse(any(method == 'POST' and endpoint == '/pulls' for method, endpoint, _ in self.calls))

    def test_repeated_diagnostic_is_read_only(self):
        original = self.request
        def duplicate(method, endpoint, payload=None, **kwargs):
            if method == 'GET' and endpoint.startswith('/pulls?'):
                return [{'title': 'LOGDMODULES_RECOVERY_TEST NON-MATHEMATICAL ' + self.identity,
                         'html_url': 'https://github.com/tpuzz/logDmodules-watchdog/pull/999'}]
            return original(method, endpoint, payload, **kwargs)
        self.api.request.side_effect = duplicate
        emit_diagnostic(self.api, self.identity)
        self.assertFalse(any(method != 'GET' for method, _, _ in self.calls))

    def test_invalid_identity_is_rejected_before_access(self):
        with self.assertRaises(ValueError): emit_diagnostic(self.api, '../unsafe')
        self.api.snapshot.assert_not_called()


class RecoveryTransportTests(unittest.TestCase):
    def setUp(self):
        fixture = test_logdmodules.LogDModulesSafetyTests()
        fixture.setUp()
        self.hb, self.owner, self.now = fixture.h, fixture.o, fixture.now
        self.snapshot = ('test-commit', self.hb, self.owner)
        self.api = Mock(repo='tpuzz/logDmodules-watchdog')
        self.api.snapshot.return_value = self.snapshot
        self.calls, self.marker = [], None
        self.api.file.side_effect = lambda path, ref: self.marker
        self.api.request.side_effect = self.request

    def request(self, method, endpoint, payload=None, **kwargs):
        self.calls.append((method, endpoint, payload))
        if method == 'GET' and endpoint.startswith('/pulls?'): return []
        if method == 'GET' and endpoint.startswith('/git/ref/'): return None
        if method == 'GET' and endpoint.startswith('/git/commits/'): return {'tree': {'sha': 'tree'}}
        if method == 'POST' and endpoint == '/git/trees':
            self.marker = json.loads(payload['tree'][0]['content'])
            return {'sha': 'new-tree'}
        if method == 'POST' and endpoint == '/git/commits': return {'sha': 'new-commit'}
        if method == 'POST' and endpoint == '/git/refs': return {}
        if method == 'POST' and endpoint == '/pulls': return {'html_url': 'fixture', **payload}
        raise AssertionError((method, endpoint))

    def test_stale_state_emits_only_recovery_marker(self):
        result = emit_recovery(self.api, self.snapshot, decide(self.hb, self.owner, self.now))
        self.assertEqual(result, 'done')
        writes = [p for method, endpoint, p in self.calls if endpoint == '/git/trees']
        self.assertEqual(len(writes[0]['tree']), 1)
        self.assertIn('watchdog/events/', writes[0]['tree'][0]['path'])
        pr = next(p for method, endpoint, p in self.calls if endpoint == '/pulls')
        self.assertTrue(pr['title'].startswith('LOGDMODULES_RECOVERY '))
        self.assertIn('DIRECT-RESUME', pr['body'])

    def test_live_owner_race_prevents_pr(self):
        changed = copy.deepcopy(self.snapshot)
        changed[2]['lease_expires_utc'] = '2099-01-01T00:00:00Z'
        self.api.snapshot.return_value = changed
        result = emit_recovery(self.api, self.snapshot, decide(self.hb, self.owner, self.now))
        self.assertEqual(result, 'changed')
        self.assertFalse(any(endpoint == '/pulls' for _, endpoint, _ in self.calls))

    def test_prior_incident_prevents_duplicate_mutation(self):
        self.api.request.side_effect = None
        self.api.request.return_value = [{'html_url': 'prior-incident'}]
        result = emit_recovery(self.api, self.snapshot, decide(self.hb, self.owner, self.now))
        self.assertEqual(result, 'done')
        self.api.request.assert_called_once()
        self.assertEqual(self.api.request.call_args.args[0], 'GET')


class PrefixSafetyTests(unittest.TestCase):
    def test_prefix_lookalikes_and_malformed_base_are_ignored(self):
        event = dict(action='opened', repository={'full_name': 'tpuzz/logDmodules-watchdog'},
                     pull_request={'title': 'LOGDMODULES_RECOVERY_EVIL x',
                                   'base': {'repo': {'full_name': 'tpuzz/logDmodules-watchdog'}}})
        self.assertEqual(classify_event(event), 'ignore')
        event['pull_request'].update(title='LOGDMODULES_RECOVERY x', base=None)
        self.assertEqual(classify_event(event), 'ignore')


if __name__ == '__main__':
    unittest.main()
