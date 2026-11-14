from rest_framework.throttling import AnonRateThrottle


class RegisterAnonThrottle(AnonRateThrottle):
    scope = 'register'
    rate = '5/hour'


class LoginAnonThrottle(AnonRateThrottle):
    scope = 'login'
    rate = '10/minute'