import importlib.util
import logging
import pathlib
import unittest

# Load the module by path so the tests do not need aiohttp or the push receiver library installed.
_PATH = pathlib.Path(__file__).resolve().parents[1] / "src" / "bluecon" / "ReceiverSupervisor.py"
_SPEC = importlib.util.spec_from_file_location("ReceiverSupervisor", _PATH)
supervisor = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(supervisor)


class FakeTimer:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class FakeEvent:
    """Stands in for threading.Event: wait() records the requested time and returns at once."""

    def __init__(self, stopAfterWaits=None):
        self.stopped = False
        self.waits = []
        self._stopAfterWaits = stopAfterWaits

    def is_set(self):
        return self.stopped

    def set(self):
        self.stopped = True

    def wait(self, seconds):
        self.waits.append(seconds)
        if self._stopAfterWaits is not None and len(self.waits) >= self._stopAfterWaits:
            self.stopped = True
        return self.stopped


class FakeReceiver:
    def __init__(self, script, ids, event):
        self.script = script
        self.initialIds = list(ids)
        self.persistent_ids = list(ids)
        self.checkin_thread = FakeTimer()
        self.socketClosed = False
        self.event = event

    def _PushReceiver__close_socket(self):
        self.socketClosed = True

    def listen(self, callback, obj):
        self.script(self)


class Harness:
    """Builds fake receivers whose behaviour is given as a list of scripts, one per receiver."""

    def __init__(self, scripts, event):
        self.scripts = list(scripts)
        self.event = event
        self.receivers = []

    def create(self, ids):
        script = self.scripts.pop(0) if self.scripts else (lambda r: r.event.set())
        receiver = FakeReceiver(script, ids, self.event)
        self.receivers.append(receiver)
        return receiver


def raising(exception, newIds=()):
    def run(receiver):
        receiver.persistent_ids.extend(newIds)
        raise exception
    return run


def returning(receiver):
    return None


def stopping(receiver):
    receiver.event.set()


class SuperviseReceiverTests(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def run_supervisor(self, scripts, event=None, clock=None, **kwargs):
        event = event or FakeEvent()
        harness = Harness(scripts, event)
        supervisor.supervise_receiver(
            create_receiver = harness.create,
            callback = lambda *a: None,
            obj = None,
            stop_event = event,
            clock = clock or (lambda: 0.0),
            **kwargs
        )
        return harness, event

    def test_reconnects_after_errors_with_growing_wait(self):
        harness, event = self.run_supervisor([
            raising(OSError("network down")),
            raising(ValueError("file descriptor cannot be a negative integer")),
            raising(ConnectionRefusedError()),
            stopping,
        ])
        self.assertEqual(len(harness.receivers), 4)
        self.assertEqual(event.waits, [10, 20, 40])

    def test_wait_is_capped(self):
        harness, event = self.run_supervisor(
            [raising(OSError())] * 6 + [stopping], max_backoff=60
        )
        self.assertEqual(event.waits, [10, 20, 40, 60, 60, 60])

    def test_listen_returning_without_error_is_treated_as_a_failure(self):
        harness, event = self.run_supervisor([returning, stopping])
        self.assertEqual(len(harness.receivers), 2)
        self.assertEqual(event.waits, [10])

    @staticmethod
    def clock_for(durations):
        """A clock where the n-th receiver run lasts durations[n] seconds (two readings per run)."""
        def readings():
            now = 0.0
            for duration in durations:
                yield now
                now += duration
                yield now
        ticks = readings()
        return lambda: next(ticks)

    def test_healthy_run_resets_the_wait(self):
        # Short, short, long (healthy), short: the wait grows, drops back to the initial value, and grows again.
        harness, event = self.run_supervisor(
            [raising(OSError())] * 4 + [stopping],
            clock = self.clock_for([1, 1, 1000, 1, 1]),
        )
        self.assertEqual(event.waits, [10, 20, 10, 20])

    def test_without_a_healthy_run_the_wait_keeps_growing(self):
        harness, event = self.run_supervisor(
            [raising(OSError())] * 4 + [stopping],
            clock = self.clock_for([1, 1, 1000, 1, 1]),
            healthy_after = 10 ** 9,
        )
        self.assertEqual(event.waits, [10, 20, 40, 80])

    def test_next_receiver_inherits_the_messages_already_seen(self):
        harness, event = self.run_supervisor([
            raising(OSError(), newIds=["m1", "m2"]),
            raising(OSError(), newIds=["m3"]),
            stopping,
        ], persistent_ids=["old"])
        self.assertEqual(harness.receivers[0].initialIds, ["old"])
        self.assertEqual(harness.receivers[1].initialIds, ["old", "m1", "m2"])
        self.assertEqual(harness.receivers[2].initialIds, ["old", "m1", "m2", "m3"])

    def test_remembered_ids_are_capped(self):
        many = [f"id{i}" for i in range(250)]
        harness, event = self.run_supervisor([raising(OSError(), newIds=many), stopping])
        self.assertEqual(len(harness.receivers[1].initialIds), supervisor.MAX_REMEMBERED_PERSISTENT_IDS)
        self.assertEqual(harness.receivers[1].initialIds[-1], "id249")

    def test_every_dead_receiver_is_torn_down(self):
        harness, event = self.run_supervisor([raising(OSError()), raising(OSError()), stopping])
        for receiver in harness.receivers:
            self.assertTrue(receiver.checkin_thread.cancelled)
            self.assertTrue(receiver.socketClosed)

    def test_error_caused_by_stopping_exits_without_reconnecting(self):
        # Closing the socket to stop the receiver makes listen() raise: that must end the loop.
        def failWhileStopping(receiver):
            receiver.event.set()
            raise ValueError("file descriptor cannot be a negative integer")
        harness, event = self.run_supervisor([failWhileStopping])
        self.assertEqual(len(harness.receivers), 1)
        self.assertEqual(event.waits, [])

    def test_stop_during_the_wait_exits_at_once(self):
        harness, event = self.run_supervisor([raising(OSError())], event=FakeEvent(stopAfterWaits=1))
        self.assertEqual(len(harness.receivers), 1)
        self.assertEqual(event.waits, [10])

    def test_does_not_start_if_already_stopped(self):
        event = FakeEvent(); event.set()
        harness, event = self.run_supervisor([raising(OSError())], event=event)
        self.assertEqual(len(harness.receivers), 0)

    def test_failure_creating_the_receiver_is_retried_too(self):
        event = FakeEvent()
        attempts = []

        def create(ids):
            attempts.append(1)
            if len(attempts) < 3:
                raise OSError("cannot build the receiver")
            event.set()
            return FakeReceiver(returning, ids, event)

        supervisor.supervise_receiver(create, lambda *a: None, None, event, clock = lambda: 0.0)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(event.waits, [10, 20])

    def test_on_receiver_is_told_about_each_new_receiver(self):
        seen = []
        event = FakeEvent()
        harness = Harness([raising(OSError()), stopping], event)
        supervisor.supervise_receiver(harness.create, lambda *a: None, None, event,
                                      on_receiver = seen.append, clock = lambda: 0.0)
        self.assertEqual(seen, harness.receivers)


class StopReceiverTests(unittest.TestCase):
    def test_tolerates_half_built_receivers(self):
        supervisor.stop_receiver(object())  # no timer, no socket helper: must not raise

    def test_swallows_errors_from_a_dead_socket(self):
        class Broken:
            checkin_thread = None

            def _PushReceiver__close_socket(self):
                raise OSError("already closed")
        supervisor.stop_receiver(Broken())


if __name__ == "__main__":
    unittest.main()
