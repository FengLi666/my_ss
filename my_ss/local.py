import logging
import socket
import struct
from typing import Tuple

from .socks import Socks5Server, SockS5Handler, ConnectionFail


class LocalServer(Socks5Server):
    def __init__(self, remote_addr: Tuple[str, int], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.remote_addr = remote_addr


class LocalHandler(SockS5Handler):
    server = None  # type: LocalServer

    def create_conn(self, addr: str, port: int):
        dest_addr, dest_port = addr, port
        server_addr, server_port = self.server.remote_addr
        logging.debug('server : remote connecting %s %s' % (server_addr, server_port))
        self.remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.remote_sock.connect_ex((server_addr, server_port)) != 0:
            raise ConnectionFail

        self.give_dest_addr_to_server(dest_addr, dest_port)

    def give_dest_addr_to_server(self, dest_addr: str, dest_port: int):
        """
         ADDR - PORT
         4    -  2
        """
        logging.debug('sslocal send dest_addr(%s:%s) to ssserver' % (dest_addr, dest_port))
        data = socket.inet_aton(dest_addr) + struct.pack('>H', dest_port)
        self.send_data(self.remote_sock, data)
