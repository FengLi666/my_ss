import socket
import logging
import selectors
from typing import Tuple

BUFF_SIZE = 2 ** 16


class StreamHandlerRecordingMixin:
    @staticmethod
    def recv_data(sock: socket.socket):
        data = b''
        try:
            data = sock.recv(BUFF_SIZE)
            logging.debug('recv %s bytes from %s:%s' % (len(data), *sock.getpeername()))
        except Exception as e:
            raise e
        finally:
            if not data:
                raise ConnectionCloseByPeer(sock.getsockname())
            return data

    @staticmethod
    def send_data(sock: socket.socket, data: bytes):
        sock.sendall(data)
        logging.debug('send %s bytes to %s:%s' % (len(data), *sock.getpeername()))


class TcpRelayer(StreamHandlerRecordingMixin):
    def __init__(self, inbound: socket.socket, outbound: socket.socket, timeout=60):
        self.local_sock = inbound
        self.remote_sock = outbound
        self.HANDLE_MAX_DURATION = timeout

    def relay(self):
        with selectors.DefaultSelector() as _sel:
            _sel.register(self.local_sock, selectors.EVENT_READ,
                          data=lambda xbytes: self.send_data(self.remote_sock, xbytes))
            _sel.register(self.remote_sock, selectors.EVENT_READ,
                          data=lambda xbytes: self.send_data(self.local_sock, xbytes))
            while 1:
                events = _sel.select(timeout=self.HANDLE_MAX_DURATION)
                if not events:
                    logging.warning('%s seconds idle, relay over' % self.HANDLE_MAX_DURATION)
                    return
                for key, event in events:
                    data = self.recv_data(key.fileobj)
                    key.data(data)

    def close(self):
        pass


class ConnectionCloseByPeer(Exception):
    def __init__(self, sock_name: Tuple[str, int]):
        self.sock_name = sock_name
