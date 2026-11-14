from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class RegisterAnonThrottle(AnonRateThrottle):
    scope = 'register'
    rate = '5/hour'


class LoginAnonThrottle(AnonRateThrottle):
    scope = 'login'
    rate = '10/minute'


class EmailVerifyUserThrottle(UserRateThrottle):
    scope = 'email_verify'
    rate = '10/hour'