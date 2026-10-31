import socket  # noqa: N999

bind = '0.0.0.0:8000'

workers = 33
threads = 132
worker_class = 'gthread'

timeout = 30
grateful_timeout = 30

keepalive = 5

max_requests = 1000
max_requests_jitter = 100

worker_tmp_dir = '/dev/shm'

accesslog = '-'
errorlog = '-'

forwarded_allow_ips = ','.join([
    socket.gethostbyname('nginx')
])