# noqa: N999
import os
import socket

bind = '0.0.0.0:8000'

workers = int(os.getenv('GUNICORN_WORKERS', '1'))
threads = int(os.getenv('GUNICORN_THREADS', '4'))
worker_class = 'gthread'

timeout = 30
graceful_timeout = 30

keepalive = 5

max_requests = 1000
max_requests_jitter = 100

worker_tmp_dir = '/dev/shm'

accesslog = '-'
errorlog = '-'

forwarded_allow_ips = ','.join([
    socket.gethostbyname('nginx')
])

control_socket_disable = True