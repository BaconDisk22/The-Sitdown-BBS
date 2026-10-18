import logging
import time

user_states = {}


def update_user_state(user_id, state):
    user_states[user_id] = state


def get_user_state(user_id):
    return user_states.get(user_id, None)


def message_chunks(message, max_bytes=200):
    """Respect the radio payload byte budget without splitting UTF-8 characters."""
    chunk = ''
    size = 0
    for character in message:
        encoded_size = len(character.encode('utf-8'))
        if size + encoded_size > max_bytes:
            yield chunk
            chunk, size = '', 0
        chunk += character
        size += encoded_size
    if chunk:
        yield chunk


def send_message(message, destination, interface):
    for chunk in message_chunks(message):
        try:
            d = interface.sendText(
                text=chunk,
                destinationId=destination,
                wantAck=True,
                wantResponse=False
            )
            destid = get_node_id_from_num(destination, interface)
            chunk = chunk.replace('\n', '\\n')
            logging.info(f"Sending message to user '{get_node_short_name(destid, interface)}' ({destid}) with sendID {d.id}: \"{chunk}\"")
        except Exception as e:
            logging.info(f"REPLY SEND ERROR {e}")

        
        time.sleep(2)


def get_node_info(interface, short_name):
    nodes = [{'num': node_id, 'shortName': node['user']['shortName'], 'longName': node['user']['longName']}
             for node_id, node in interface.nodes.items()
             if node['user']['shortName'].lower() == short_name]
    return nodes


def get_node_id_from_num(node_num, interface):
    for node_id, node in interface.nodes.items():
        if node.get('num') == node_num:
            return node_id
    return None


def get_node_short_name(node_id, interface):
    node_info = interface.nodes.get(node_id)
    if node_info:
        return node_info.get('user', {}).get('shortName')
    return None


def send_bulletin_to_bbs_nodes(board, sender_short_name, subject, content, unique_id, bbs_nodes, interface):
    message = f"BULLETIN|{board}|{sender_short_name}|{subject}|{content}|{unique_id}"
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_mail_to_bbs_nodes(sender_id, sender_short_name, recipient_id, subject, content, unique_id, bbs_nodes,
                           interface):
    message = f"MAIL|{sender_id}|{sender_short_name}|{recipient_id}|{subject}|{content}|{unique_id}"
    logging.info(f"SERVER SYNC: Syncing new mail message {subject} sent from {sender_short_name} to other BBS systems.")
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_delete_bulletin_to_bbs_nodes(bulletin_id, bbs_nodes, interface):
    message = f"DELETE_BULLETIN|{bulletin_id}"
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_delete_mail_to_bbs_nodes(unique_id, bbs_nodes, interface):
    message = f"DELETE_MAIL|{unique_id}"
    logging.info(f"SERVER SYNC: Sending delete mail sync message with unique_id: {unique_id}")
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)


def send_channel_to_bbs_nodes(name, url, bbs_nodes, interface):
    message = f"CHANNEL|{name}|{url}"
    for node_id in bbs_nodes:
        send_message(message, node_id, interface)
