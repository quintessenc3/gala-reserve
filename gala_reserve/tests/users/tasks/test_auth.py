from apps.users.tasks.auth import send_verification_email
from django.conf import settings


class TestSendVerificationEmail:
    def test_send_verification_email(self, mailoutbox):
        send_verification_email('user@example.com', '842512', 15)

        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.to == ['user@example.com']
        assert mail.from_email == settings.DEFAULT_FROM_EMAIL
        assert mail.subject
        assert '842512' in mail.body        
