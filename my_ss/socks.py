import logging
import socket
import struct
import threading
import time
from socketserver import BaseRequestHandler, ThreadingTCPServer
from .tcp_relayer import StreamHandlerRecordingMixin, TcpRelayer, ConnectionCloseByPeer

BUFF_SIZE = 1024 * 16


class Socks5Server(ThreadingTCPServer):
    pass


class BadSocksHeaderException(Exception):
    def __init__(self, stage, *args):
        super().__init__(*args)
        self.stage = stage


class ConnectionFail(Exception):
    pass


# noinspection SpellCheckingInspection


class SockS5Handler(BaseRequestHandler, StreamHandlerRecordingMixin):
    remote_sock = None  # type: socket.socket
    HANDLE_MAX_DURATION = 60

    # noinspection PyMissingConstructor
    def __init__(self, request: socket.socket, client_address, server):
        self.request = request
        self.last_update_time = time.time()
        self.local_sock = self.request
        self.client_address = client_address
        self.server = server
        self.host = None

        self.setup()
        try:
            self.handle_start_time = time.time()
            self.handle()
        finally:
            self.finish()

    def _write_to_sock(self, data: bytes):
        self.local_sock.sendall(data)

    def handle(self):
        try:
            self.handle_socks5_init()
            self.handle_socks5_addr()
            self.create_conn(self.dest_addr, self.dest_port)
            relayer = TcpRelayer(self.local_sock, self.remote_sock, timeout=60)
            logging.debug('server : start communicating...')
            relayer.relay()
            relayer.close()
        except BadSocksHeaderException as bdh:
            logging.warning('request from %s:%s has a bad socks5 header in %s stage'
                            % (*self.local_sock.getpeername(), bdh.stage))
        except ConnectionFail:
            logging.warning("cannot connect %s:%s" % (self.dest_addr, self.dest_port))
        except ConnectionCloseByPeer as ccp:
            logging.warning('peer %s:%s close connection' % (*ccp.sock_name,))
        except Exception as e:
            raise e

    def handle_socks5_init(self):
        logging.info(
            'handle socks_init from %s:%s with %s' % (
                *self.local_sock.getpeername(), threading.current_thread().getName()))
        data = self.recv_data(self.local_sock)
        if len(data) < 3 or data[0] != 5 or data[1] < 1:
            raise BadSocksHeaderException
        methods = data[2:]
        if b'\x00' in methods:
            self.send_data(self.local_sock, b'\x05\x00')
        else:
            self.send_data(self.local_sock, b'\x05\xff')

    def handle_socks5_addr(self):
        data = self.recv_data(self.local_sock)
        logging.debug('server : address accepting')
        self.dest_addr, self.dest_port = self.parse_socks5_addr_header(data)
        logging.info('recv addr req to %s:%s from %s:%s' % (
            self.host or self.dest_addr, self.dest_port, *self.local_sock.getpeername()))
        replay = self.build_socks5_addr_reply()
        self.send_data(self.local_sock, replay)

    def parse_socks5_addr_header(self, data: bytes) -> (bytes, int):
        """
        :param data: bytes
        :return: (bytes,int)
                (a string format  ip or host, port)
        """
        '''
        +----+-----+-------+------+----------+----------+
        |VER | CMD |  RSV  | ATYP | DST.ADDR | DST.PORT |
        +----+-----+-------+------+----------+----------+
        | 1  |  1  | X'00' |  1   | Variable |    2     |
        +----+-----+-------+------+----------+----------+
        CMD
             o  CONNECT X'01'
             o  BIND X'02'
             o  UDP ASSOCIATE X'03'
        ATYP   address type of following address
             o  IP V4 address: X'01'
        DST.ADDR     IP V4 with a length of 4 octets
        '''
        if len(data) < 10:
            logging.debug('server : bad header')
            raise BadSocksHeaderException

        if data[0] != 5:
            raise BadSocksHeaderException
        if data[1] != 1:
            raise NotImplemented
        if data[3] == 4:
            raise NotImplemented

        if data[3] == 1:
            DST_ADDR = data[4:8]
            DST_ADDR = socket.inet_ntoa(DST_ADDR)
        elif data[3] == 3:
            DST_ADDR_LEN = data[4]
            DST_ADDR = data[5:5 + DST_ADDR_LEN]
            self.host = DST_ADDR
            DST_ADDR = socket.gethostbyname(DST_ADDR.decode('utf-8'))
        else:
            raise BadSocksHeaderException

        return DST_ADDR, struct.unpack('>H', data[-2:])[0]

    def build_socks5_addr_reply(self) -> bytes:
        """
                +----+-----+-------+------+----------+----------+
                |VER | REP |  RSV  | ATYP | BND.ADDR | BND.PORT |
                +----+-----+-------+------+----------+----------+
                | 1  |  1  | X'00' |  1   | Variable |    2     |
                +----+-----+-------+------+----------+----------+
                """
        addr, port = self.dest_addr, self.dest_port
        addr_bytes = socket.inet_aton(addr)
        port_bytes = struct.pack('>H', port)
        reply = b'\x05\x00\x00\x01' + addr_bytes + port_bytes
        return reply

    def create_conn(self, addr: str, port: int):
        logging.debug('server : remote connecting %s %s' % (addr, port))
        self.remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.remote_sock.connect_ex((addr, port)) != 0:
            raise ConnectionFail

    def finish(self):
        logging.info('handle complete for %s:%s in %s seconds', *self.local_sock.getpeername(),
                     time.time() - self.handle_start_time)
        if getattr(self, 'remote_sock'):
            self.remote_sock.close()
        self.local_sock.close()
