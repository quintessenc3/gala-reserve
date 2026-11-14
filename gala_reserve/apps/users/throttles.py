from rest_framework.throttling import AnonRateThrottle


class RegisterAnonThrottle(AnonRateThrottle):
    scope = 'register'
    rate = '5/hour'