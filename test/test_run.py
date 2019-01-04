import gevent.monkey

gevent.monkey.patch_all()

import logging
import time

logging.basicConfig(format='%(asctime)s %(levelname)s:   %(message)s', level=logging.INFO)
from my_ss.socks import Socks5Server, SockS5Handler
from threading import Thread

import random, string

# from flask import Flask, Response
#
# app = Flask('test_run')
#
#
# @app.route('/<int:num>')
# def echo(num):
#     time.sleep(3)
#     r = Response(
#         str(num) + ' ' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=2 ** 10)),
#         mimetype='text/plain')
#     return r
#
#
# Thread(target=app.run, args=(('127.0.0.1', 8778)), kwargs={'threaded': True}).start()

ss = Socks5Server(('127.0.0.1', 55544), SockS5Handler)
ss.serve_forever()
