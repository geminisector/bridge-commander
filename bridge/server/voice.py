"""The voice room a table shares.

The room id is **derived, never stored**: a UUIDv5 over the game room and the
mission it is playing.  That has three consequences worth spelling out:

* every client ends up in the same call with no coordination and no server
  bookkeeping — the value is a pure function of state they all already have;
* it survives restarts, reloads and reconnects, because nothing is persisted to
  lose;
* it is mission-scoped, so switching missions moves the crew to a fresh room
  rather than dropping a new game into the previous one's channel.

It is a *name*, not a secret.  Anyone who knows the channel, instance and mission
ids can derive it, so it hides a room from casual guessing but is not a
credential; treat a private table as needing a private Jitsi deployment.
"""

from __future__ import annotations

import uuid

#: Fixed namespace, so a derived id is stable across restarts and deployments.
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "bridge-commander/voice")


def voice_room(channel_id: str, instance_id: str, campaign_id: str) -> str:
    """The UUID everyone in this room, on this mission, joins."""
    name = f"{channel_id}/{instance_id}/{campaign_id}"
    return str(uuid.uuid5(NAMESPACE, name))


__all__ = ["NAMESPACE", "voice_room"]
