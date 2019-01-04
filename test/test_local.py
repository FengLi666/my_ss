import random
import socket
import logging

logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s.%(funcName)s:   %(message)s', level=logging.DEBUG)
import string

from .test_socks import Sock5HandlerTest, SimpleEchoHandler
from my_ss.server import SSServer, SSHandler
from my_ss.local import LocalServer, LocalHandler
from socketserver import TCPServer
import threading


class LocalHandlerTest(Sock5HandlerTest):
    def setUp(self):
        self.lss_name = ('127.0.0.1', 24444)
        self.ssss_name = ('127.0.0.1', 25555)
        self.es_name = ('127.0.0.1', 26666)
        self.local_server = LocalServer(self.ssss_name, self.lss_name, LocalHandler)
        self.ssserver = SSServer(self.ssss_name, SSHandler)
        self.echo_server = TCPServer(self.es_name, SimpleEchoHandler)
        self.st0 = threading.Thread(target=self.local_server.serve_forever)
        self.st1 = threading.Thread(target=self.ssserver.serve_forever)
        self.st2 = threading.Thread(target=self.echo_server.serve_forever)
        self.st0.daemon = True
        self.st1.daemon = True
        self.st2.daemon = True
        self.st0.start()
        self.st1.start()
        self.st2.start()

    def test_all(self):
        for i in range(10):
            with self.subTest(i=i):
                with socket.socket() as sock:
                    self.client_sock = sock
                    self.auth(self.lss_name)
                    self.addr(self.es_name)
                    up = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(2 ** 10)).encode(
                        'utf-8')
                    sock.sendall(up)
                    down = sock.recv(2 ** 16)
                    self.assertEqual(up, down)

    def tearDown(self):
        pass
