"""Human-readable radio transport troubleshooting, without exposing credentials."""
import re


def explain_transport_error(message, mode="serial"):
    """Return a short safe hint based on a logged transport error."""
    text = str(message).lower()
    if any(term in text for term in ("no route to host", "network is unreachable")):
        return "Radio network unreachable. Check the radio IP, Wi-Fi/network, and routing."
    if "connection refused" in text:
        return "Radio refused the TCP connection. Check its IP, TCP port, and radio service."
    if any(term in text for term in ("timed out", "timeout")):
        return "Radio connection timed out. Check power, network reachability, and endpoint."
    if any(term in text for term in ("connection reset", "broken pipe")):
        return "Radio connection dropped. Check radio power and cable/network stability."
    if any(term in text for term in ("permission denied", "access denied")):
        return "Device access denied. Check USB permissions and whether another app uses the port."
    if any(term in text for term in ("no such file or directory", "could not open port")):
        return "Serial device not found. Reconnect the USB radio and select the correct port."
    return "Radio transport error. Check the server log and connection settings."
