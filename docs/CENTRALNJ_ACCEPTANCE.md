# CentralNJ Intel Mac acceptance checklist

This is a manual acceptance plan, not evidence of successful hardware tests.

## Preconditions
- Use an Intel x86_64 Mac with a supported Meshtastic radio.
- Never commit channel keys, MQTT credentials, node identifiers, or broker passwords.
- Leave optional MQTT monitoring and transmissions disabled until explicitly configured.
- Keep a second independent radio available to verify actual delivery.

## Checks
1. Launch the signed or unsigned test build and verify Jersey dashboard layout and navigation.
2. Confirm Demo mode never connects, publishes MQTT, or sends radio packets.
3. Check TCP reachability with the BBS stopped; note that reachable does not prove Meshtastic protocol.
4. Enumerate USB devices without opening or reconfiguring a serial port.
5. Start the BBS with the operator's radio and confirm the Meshtastic SDK connection.
6. Enable the receive-only MQTT monitor explicitly, verify narrow topic selection, and check connection and activity timestamps.
7. Disconnect and reconnect the network; verify bounded retries and an operator stop that cancels recovery.
8. Confirm sending remains denied until opt-in and operator confirmation; never automatically publish on reconnect.
9. Send a deliberate test message from the configured radio and confirm receipt on an independent radio.
10. Send a reply from that independent radio and confirm BBS receipt; record channel, date, device firmware, and result without secrets.

## Result classification
- **Not run:** no real hardware test performed
- **Transport reachable:** TCP/USB observed, no protocol proof
- **Protocol connected:** Meshtastic session confirmed, no delivery proof
- **Two-way verified:** independent radios observed both directions in the current test session

Record each result with UTC timestamp, app commit, OS, radio firmware, and operator initials. Never mark two-way verified based on MQTT subscription activity alone.
