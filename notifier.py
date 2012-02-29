import time
import gevent
from gevent_zeromq import zmq
from flask import Flask, request, jsonify, session

zmq_context = zmq.Context()
socket_pub = zmq_context.socket(zmq.PUSH)
socket_pub.connect('tcp://127.0.0.1:6666')
socket_sub = zmq_context.socket(zmq.SUB)
socket_sub.setsockopt(zmq.SUBSCRIBE, '')
socket_sub.connect('tcp://127.0.0.1:6665')

app = Flask(__name__)
app.config.from_envvar('NOTIFIER_SETTINGS')
POLL_TIMEOUT = app.config.get('POLL_TIMEOUT', 10)

update_event = gevent.event.Event()
last_message_at = 0

def notify_update():
	global last_message_at
	last_message_at = time.time()
	update_event.set()
	update_event.clear()

@app.route('/updates')
def updates():
	if last_message_at > session.get('last_update_at', last_message_at):
		session['last_update_at'] = last_message_at
		return 'true'

	last_update_at = last_message_at
	update_event.wait(POLL_TIMEOUT)
	if last_update_at < last_message_at:
		session['last_update_at'] = last_message_at
		return 'true'
	return 'false'

@app.route('/updates', methods=['POST'])
def send_message():
	if 'username' not in session:
		abort(403)

	lines = request.form['message'].splitlines()
	nick = session['username'].encode('utf-8')
	channels = '#nakji' #XXX
	for line in lines:
		socket_pub.send('PRIVMSG %s :<%s> %s' % (channels, nick, line.encode('utf-8')))
	notify_update()
	return 'true'

if __name__ == '__main__':
	from gevent.pywsgi import WSGIServer
	server = WSGIServer(('', 8888), app)
	gevent.spawn(server.serve_forever)

	while True:
		msg = socket_sub.recv()
		if 'PRIVMSG' in msg:
			notify_update()