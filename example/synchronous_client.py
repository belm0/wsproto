'''
The client reads a line from stdin, sends it to the server, then prints the
response. This is a poor implementation of a client. It is only intended to
demonstrate how to use wsproto.
'''

import socket
import sys

from wsproto.connection import ConnectionType, WSConnection
from wsproto.events import ConnectionEstablished, TextReceived, PongReceived


RECEIVE_BYTES = 4096


def main():
    ''' Run the client. '''
    try:
        host = sys.argv[1]
        port = int(sys.argv[2])
    except (IndexError, ValueError):
        print('Usage: {} <HOST> <PORT>'.format(sys.argv[0]))
        sys.exit(1)

    try:
        wsproto_demo(host, port)
    except KeyboardInterrupt:
        print('\nReceived SIGINT: shutting down…')


def wsproto_demo(host, port):
    '''
    Demonstrate wsproto:

    0) Open TCP connection
    1) Negotiate WebSocket opening handshake
    2) Send a message and display response
    3) Send ping and display pong
    4) Negotiate WebSocket closing handshake

    :param stream: a socket stream
    '''

    # 0) Open TCP connection
    print('Connecting to {}:{}'.format(host, port))
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((host, port))

    # 1) Negotiate WebSocket opening handshake
    print('Opening WebSocket')
    ws = WSConnection(ConnectionType.CLIENT, host=host, resource='server')

    # events is a generator that yields websocket event objects. Usually you
    # would say `for event in ws.events()`, but the synchronous nature of this
    # client requires us to use next(event) instead so that we can interleave
    # the network I/O. It will raise StopIteration when it runs out of events
    # (i.e. needs more network data), but since this script is synchronous, we
    # will explicitly resume the generator whenever we have new network data.
    events = ws.events()

    # Because this is a client WebSocket, wsproto has automatically queued up
    # a handshake, and we need to send it and wait for a response.
    net_send_recv(ws, conn)
    event = next(events)
    if isinstance(event, ConnectionEstablished):
        print('WebSocket negotiation complete')
    else:
        raise Exception('Expected ConnectionEstablished event!')

    # 2) Send a message and display response
    message = "wsproto is great"
    print('Sending message: {}'.format(message))
    ws.send_data(message)
    net_send_recv(ws, conn)
    event = next(events)
    if isinstance(event, TextReceived):
        print('Received message: {}'.format(event.data))
    else:
        raise Exception('Expected TextReceived event!')

    # 3) Send ping and display pong
    payload = b"table tennis"
    print('Sending ping: {}'.format(payload))
    ws.ping(payload)
    net_send_recv(ws, conn)
    event = next(events)
    if isinstance(event, PongReceived):
        print('Received pong: {}'.format(event.payload))
    else:
        raise Exception('Expected PongReceived event!')

    # 4) Negotiate WebSocket closing handshake
    print('Closing WebSocket')
    ws.close(code=1000, reason='sample reason')
    # After sending the closing frame, we won't get any more events. The server
    # should send a reply and then close the connection, so we need to receive
    # twice:
    net_send_recv(ws, conn)
    conn.shutdown(socket.SHUT_WR)
    net_recv(ws, conn)


def net_send(ws, conn):
    ''' Write pending data from websocket to network. '''
    out_data = ws.bytes_to_send()
    print('Sending {} bytes'.format(len(out_data)))
    conn.send(out_data)


def net_recv(ws, conn):
    ''' Read pending data from network into websocket. '''
    in_data = conn.recv(RECEIVE_BYTES)
    if in_data:
        # A receive of zero bytes indicates the TCP socket has been closed. We
        # need to pass None to wsproto to update its internal state.
        print('Received 0 bytes (connection closed)')
        ws.receive_bytes(None)
    else:
        print('Received {} bytes'.format(len(in_data)))
        ws.receive_bytes(in_data)


def net_send_recv(ws, conn):
    ''' Send pending data and then wait for response. '''
    net_send(ws, conn)
    net_recv(ws, conn)


if __name__ == '__main__':
    main()
