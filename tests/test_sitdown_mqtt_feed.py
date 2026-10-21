"""Offline per-network MQTT feed and desktop drain tests."""
import unittest
from unittest.mock import Mock
import sitdown_desktop as desktop
from sitdown_mqtt_envelope import EnvelopeSummary
from sitdown_mqtt_feed import MeshFeed, FeedEntry, format_entry
from sitdown_mqtt_pipeline import ProcessingResult


def accepted(network='centralnj', encrypted=True, portnum=None, from_id=0x7b, to_id=0xFFFFFFFF):
    summary = EnvelopeSummary('!12345678', 'LongFast', 7, from_id, to_id, encrypted, portnum)
    reason = 'Encrypted metadata only' if encrypted else 'Decoded metadata only'
    return ProcessingResult(True, reason, network, summary)


class FeedFormattingTests(unittest.TestCase):
    def test_encrypted_entry_shows_metadata_only(self):
        text = format_entry(FeedEntry(0, accepted()))
        self.assertIn('from !0000007b → broadcast', text)
        self.assertIn('ch LongFast', text)
        self.assertIn('via !12345678', text)
        self.assertIn('ENCRYPTED — not decrypted', text)

    def test_decoded_entry_names_port_but_not_content(self):
        text = format_entry(FeedEntry(0, accepted(encrypted=False, portnum=1, to_id=0x1c8)))
        self.assertIn('→ !000001c8', text)
        self.assertIn('TEXT_MESSAGE_APP — content not displayed', text)

    def test_rejection_shows_reason(self):
        text = format_entry(FeedEntry(0, ProcessingResult(False, 'Invalid MQTT envelope', 'sjmesh')))
        self.assertIn('REJECTED — Invalid MQTT envelope', text)


class MeshFeedTests(unittest.TestCase):
    def test_networks_are_kept_apart_and_newest_first(self):
        feed = MeshFeed(clock=iter(range(10)).__next__)
        feed.add('centralnj', accepted(from_id=1))
        feed.add('centralnj', accepted(from_id=2))
        feed.add('sjmesh', accepted('sjmesh', from_id=3))
        self.assertEqual([e.result.summary.from_id for e in feed.entries('centralnj')], [2, 1])
        self.assertEqual([e.result.summary.from_id for e in feed.entries('sjmesh')], [3])

    def test_duplicates_and_unknown_networks_are_not_listed(self):
        feed = MeshFeed()
        self.assertFalse(feed.add('centralnj', ProcessingResult(False, 'Duplicate packet', 'centralnj')))
        self.assertFalse(feed.add('other', accepted()))
        self.assertEqual(feed.entries('centralnj'), [])

    def test_feed_is_bounded(self):
        feed = MeshFeed(limit=3)
        for i in range(5):
            feed.add('sjmesh', accepted('sjmesh', from_id=i))
        self.assertEqual([e.result.summary.from_id for e in feed.entries('sjmesh')], [4, 3, 2])

    def test_empty_render_explains_how_to_connect(self):
        self.assertIn('No packets received', MeshFeed().render('sjmesh'))


class DesktopDrainTests(unittest.TestCase):
    def app(self, events):
        app = desktop.SitdownApp.__new__(desktop.SitdownApp)
        app.mesh_feed = MeshFeed()
        app.dual_mqtt = Mock(drain_events=Mock(return_value=events))
        app.wire_views = {name: Mock(winfo_exists=Mock(return_value=True), yview=Mock(return_value=(0.0, 1.0)))
                          for name in ('centralnj', 'sjmesh')}
        return app

    def test_drain_updates_only_the_receiving_network_view(self):
        app = self.app([('centralnj', accepted())])
        app.drain_mqtt_events()
        app.dual_mqtt.drain_events.assert_called_once_with(limit=50)
        inserted = app.wire_views['centralnj'].insert.call_args.args[1]
        self.assertIn('from !0000007b', inserted)
        app.wire_views['sjmesh'].insert.assert_not_called()

    def test_drain_without_open_wire_page_still_records(self):
        app = self.app([('sjmesh', accepted('sjmesh'))])
        app.wire_views = {}
        app.drain_mqtt_events()
        self.assertEqual(len(app.mesh_feed.entries('sjmesh')), 1)

    def test_no_broker_session_is_a_no_op(self):
        app = desktop.SitdownApp.__new__(desktop.SitdownApp)
        app.dual_mqtt = None
        app.drain_mqtt_events()


if __name__ == '__main__':
    unittest.main()
