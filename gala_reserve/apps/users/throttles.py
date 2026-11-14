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


class EmailResendPauseUserThrottle(UserRateThrottle):
    scope = 'email_resend_pause'
    rate = '1/minute'


class EmailResendUserThrottle(UserRateThrottle):
    scope = 'email_resend'
    rate = '3/hour'


class PasswordResetAnonThrottle(AnonRateThrottle):
    scope = 'password_reset'
    rate = '5/hour'


class PasswordResetUserThrottle(UserRateThrottle):
    scope = 'password_reset_user'
    rate = '5/hour'