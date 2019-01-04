import logging
import socket
from socketserver import ThreadingTCPServer, BaseRequestHandler

from my_ss.common import int_from_bytes
from my_ss.socks import ConnectionFail
from my_ss.tcp_relayer import StreamHandlerRecordingMixin, ConnectionCloseByPeer
from my_ss.tcp_relayer import TcpRelayer


class ServerBadDestAddr(Exception):
    pass


class SSServer(ThreadingTCPServer):
    pass


class SSHandler(BaseRequestHandler, StreamHandlerRecordingMixin):
    # noinspection PyMissingConstructor
    def __init__(self, request, client_address, server):
        self.request = request
        self.client_address = client_address
        self.server = server
        self.setup()
        try:
            self.handle()
        finally:
            self.finish()

    def handle(self):
        try:
            self.handle_addr()
            self.create_conn(self.dest_addr, self.dest_port)
            relayer = TcpRelayer(self.request, self.remote_sock)
            relayer.relay()
            relayer.close()
        except ServerBadDestAddr as bdh:
            logging.warning('addr request from local %s:%s is bad'
                            % (*self.request.getpeername(),))
        except ConnectionFail:
            logging.warning("cannot connect %s:%s" % (self.dest_addr, self.dest_port))
        except ConnectionCloseByPeer as ccp:
            logging.warning('peer %s:%s close connection' % (*ccp.sock_name,))
        except Exception as e:
            raise e

    def handle_addr(self):
        data = self.recv_data(self.request)
        self.parse_adr(data)

    def parse_adr(self, data):
        if len(data) < 6:
            raise ServerBadDestAddr
        dest_addr, dest_port = data[:4], data[4:]
        self.dest_addr = socket.inet_ntoa(dest_addr)
        self.dest_port = int_from_bytes(dest_port)
        if not (0 < self.dest_port < 65536):
            raise ServerBadDestAddr

    def create_conn(self, addr: str, port: int):
        logging.debug('server : remote connecting %s %s' % (self.dest_addr, self.dest_port))
        self.remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.remote_sock.connect_ex((addr, port)) != 0:
            raise ConnectionFail
