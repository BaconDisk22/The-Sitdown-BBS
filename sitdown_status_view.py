"""Read-only CentralNJ operator status; no transport side effects."""
from sitdown_connection_status import Observation, describe_status


def format_operator_status(radio_state="unverified", mqtt_state="disabled"):
    summary = describe_status(Observation(radio_state), Observation(mqtt_state))
    return ("Radio: {radio}\nMQTT monitor: {mqtt}\nTwo-way: {delivery}"
            .format(radio=summary["radio"]["state"],
                    mqtt=summary["mqtt_monitor"]["state"],
                    delivery=summary["two_way_delivery"]))
