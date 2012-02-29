import gevent.monkey; gevent.monkey.patch_all()

import os
import time
import datetime
import socket
import logging
import gevent
from gevent_zeromq import zmq

IRC_HOST = 'irc.ozinger.org'
IRC_PORT = 6667
IRC_NICK = 'nakji'
IRC_ENCODING = 'utf-8'
IRC_CHANNELS = '#nakji'
LOG_PATH = 'rawlog'
ZMQ_PUB_LISTEN_ADDR = 'tcp://127.0.0.1:6665'
ZMQ_SUB_LISTEN_ADDR = 'tcp://127.0.0.1:6666'

zmq_context = zmq.Context()
zmq_socket = zmq_context.socket(zmq.PUB)
zmq_socket.bind(ZMQ_PUB_LISTEN_ADDR)
conn = socket.create_connection((IRC_HOST, IRC_PORT))

log_file_date = None
log_file = None

def get_log_file(date):
    global log_file_date, log_file

    if not log_file_date:
        if os.path.exists(LOG_PATH):
            mtime = os.stat(LOG_PATH).st_mtime
            log_file_date = datetime.datetime.fromtimestamp(mtime).date()
        else:
            log_file_date = date

    if log_file_date != date:
        rotate_log()
        log_file_date = date

    if not log_file:
        log_file = open(LOG_PATH, 'a')

    return log_file

def rotate_log():
    global log_file_date, log_file
    if log_file:
        log_file.close()
        log_file = None
    os.rename(LOG_PATH, LOG_PATH + '.' + log_file_date.strftime("%Y%m%d"))

def log(line):
    now = datetime.datetime.now()
    fp = get_log_file(now.date())
    fp.write('[%s] %s\n' % (now.isoformat(), line.encode('utf-8')))
    fp.flush()
    print line

def recv_line(line):
    parts = line.split(' ', 2)
    if parts[0] == 'PING':
        send_line('PONG ' + parts[1], silent=True)
    else:
        if len(parts) >= 2 and parts[0].startswith(':') and parts[1] == '001':
            send_line('JOIN ' + IRC_CHANNELS)
            gevent.spawn(zmq_listener)

        log(u'<<< ' + line)
        zmq_socket.send(line.encode('utf-8'))

def send_line(line, silent=False):
    conn.send(line.encode(IRC_ENCODING) + '\r\n')
    if not silent:
        log(u'>>> ' + line)

def zmq_listener():
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.bind(ZMQ_SUB_LISTEN_ADDR)
    while True:
        msg = socket.recv()
        if '\n' in msg or '\r' in msg:
            continue
        send_line(msg.decode('utf-8'))

send_line(u'USER bot 0 * :nakji')
send_line(u'NICK ' + IRC_NICK)
while True:
    data = conn.recv(4096)
    if not data: break
    lines = data.split('\r\n')
    for line in lines:
        if line:
            recv_line(line.decode(IRC_ENCODING))
conn.close()
