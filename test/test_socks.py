if 0:
    import gevent.monkey

    gevent.monkey.patch_all()

import logging
import unittest
import random, string

logging.basicConfig(format='%(asctime)s %(levelname)s:   %(message)s', level=logging.DEBUG)
import struct
from typing import Tuple
from my_ss.socks import SockS5Handler, Socks5Server

import socket
from socketserver import StreamRequestHandler
from my_ss.common import int_to_bytes

BUF_SIZE = 1024 * 16


class SimpleEchoHandler(StreamRequestHandler):
    def handle(self):
        data = self.request.recv(BUF_SIZE)
        self.request.sendall(data)


class Sock5HandlerTest(unittest.TestCase):
    def setUp(self):
        from socketserver import TCPServer
        from threading import Thread
        self.socks_server_addr = ('127.0.0.1', 23382)
        self.echo_server_addr = ('127.0.0.1', 23383)
        self.socks_server = Socks5Server(self.socks_server_addr, SockS5Handler)
        self.echo_server = TCPServer(self.echo_server_addr, SimpleEchoHandler)
        self.client_sock = socket.socket()
        self.st = Thread(target=self.socks_server.serve_forever)
        self.st2 = Thread(target=self.echo_server.serve_forever)
        self.st.daemon = True
        self.st2.daemon = True
        self.st.start()
        self.st2.start()

    def test_pp_server(self):
        for i in range(4, 12):
            with self.subTest(i=i):
                with socket.create_connection(self.echo_server_addr) as sock:
                    up = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(2 ** i)).encode(
                        'utf-8')
                    sock.sendall(up)
                    down = sock.recv(max(BUF_SIZE, 2 ** i))
                    self.assertEqual(up, down)

    def test_communicate(self):
        for j in range(10):
            for i in range(5, 12):
                with self.subTest(id=8 * j + i):
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        self.client_sock = sock
                        self.auth(self.socks_server_addr)
                        self.addr(self.echo_server_addr)

                        logging.debug('try communicate data')
                        up = ''.join(
                            random.choice(string.ascii_uppercase + string.digits) for _ in range(2 ** i)).encode(
                            'utf-8')
                        self.client_sock.sendall(up)
                        down, tmp = b'', b'_'
                        while len(tmp) != 0:
                            tmp = self.client_sock.recv(BUF_SIZE)
                            down += tmp

                        self.assertEqual(up, down)

    def auth(self, auth_addr):
        socket_init_msg = b'\x05\x01\x00'

        logging.debug('try connect')
        self.client_sock.connect(auth_addr)
        self.client_sock.sendall(socket_init_msg)
        logging.debug('try recv from server')
        data = self.client_sock.recv(BUF_SIZE)
        self.assertEqual(data, b'\x05\x00')

    def test_auth(self):
        self.auth(self.socks_server_addr)

    def addr(self, addr: Tuple[str, int], is_ip=True, ):
        logging.debug('try request with addr')
        if is_ip:
            address_bytes = socket.inet_aton(addr[0]) + struct.pack('>H', addr[1])
            addr_req = b'\x05\x01\x00\x01' + address_bytes
        else:
            address_bytes = int_to_bytes(len(addr[0])) + addr[0].encode('utf-8') + struct.pack('>H', addr[1])
            addr_req = b'\x05\x01\x00\x03' + address_bytes
            address_bytes = socket.inet_aton(socket.gethostbyname(addr[0])) + struct.pack('>H', addr[1])

        self.client_sock.sendall(addr_req)
        data = self.client_sock.recv(BUF_SIZE)
        self.assertEqual(address_bytes, data[4:])

    def test_addr(self):
        self.auth(self.socks_server_addr)
        self.addr(('localhost', 1), is_ip=False)

    def tearDown(self):
        self.client_sock.close()


if __name__ == '__main__':
    unittest.main()
