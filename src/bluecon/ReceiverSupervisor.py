from __future__ import annotations

import logging
import time
from typing import Any, Callable

_LOGGER = logging.getLogger(__name__)

INITIAL_BACKOFF_SECONDS = 10
MAX_BACKOFF_SECONDS = 300
# A receiver that stayed up at least this long counts as healthy: the next failure starts from the initial wait again.
HEALTHY_AFTER_SECONDS = 300
# Persistent ids are handed to the next receiver so that Google does not redeliver (and Home Assistant does not
# re-trigger) messages that were already handled. The list is capped so it cannot grow forever.
MAX_REMEMBERED_PERSISTENT_IDS = 100


def stop_receiver(receiver: Any) -> None:
    """Stop the keep-alive timer of a push receiver and close its socket.

    Closing the socket also wakes up a `listen()` call that is blocked waiting for data. Every step is guarded,
    since the receiver may already be half closed."""

    timer = getattr(receiver, "checkin_thread", None)
    if timer is not None:
        try:
            timer.cancel()
        except Exception:
            _LOGGER.debug("Could not cancel the keep-alive timer", exc_info = True)

    closeSocket = getattr(receiver, "_PushReceiver__close_socket", None)
    if closeSocket is not None:
        try:
            closeSocket()
        except Exception:
            _LOGGER.debug("Could not close the push receiver socket", exc_info = True)


def supervise_receiver(
    create_receiver: Callable[[list[str]], Any],
    callback: Callable[..., None],
    obj: Any,
    stop_event: Any,
    persistent_ids: list[str] | None = None,
    on_receiver: Callable[[Any], None] | None = None,
    initial_backoff: float = INITIAL_BACKOFF_SECONDS,
    max_backoff: float = MAX_BACKOFF_SECONDS,
    healthy_after: float = HEALTHY_AFTER_SECONDS,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """Run a push receiver until `stop_event` is set, building a new one whenever it stops.

    `listen()` is meant to never return. If it raises, or returns, the receiver is torn down and a new one is
    created after a growing wait (initial_backoff, doubled each time, up to max_backoff).

    This blocks, so it is meant to run in its own thread or executor job."""

    knownIds: list[str] = list(persistent_ids or [])
    backoff = initial_backoff

    while not stop_event.is_set():
        receiver = None
        startedAt = clock()
        try:
            receiver = create_receiver(list(knownIds))
            if on_receiver is not None:
                on_receiver(receiver)
            _LOGGER.info("FCM push receiver starting to listen")
            receiver.listen(callback, obj)
            if not stop_event.is_set():
                _LOGGER.warning("FCM push receiver stopped listening without an error")
        except Exception:
            if not stop_event.is_set():
                _LOGGER.exception("FCM push receiver stopped unexpectedly")
        finally:
            if receiver is not None:
                for persistentId in getattr(receiver, "persistent_ids", []):
                    if persistentId not in knownIds:
                        knownIds.append(persistentId)
                knownIds = knownIds[-MAX_REMEMBERED_PERSISTENT_IDS:]
                stop_receiver(receiver)

        if stop_event.is_set():
            break

        if clock() - startedAt >= healthy_after:
            backoff = initial_backoff

        _LOGGER.warning("Reconnecting the FCM push receiver in %s seconds", backoff)
        if stop_event.wait(backoff):
            break
        backoff = min(backoff * 2, max_backoff)

    _LOGGER.info("FCM push receiver supervisor stopped")
