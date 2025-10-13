# Phone Verification App

This app handles customer phone verification for the booking flow.

## SMS Providers

Two SMS providers are available out of the box:

- `phone_verification.sms.dummy.DummySmsProvider` logs outgoing messages (default).
- `phone_verification.sms.twilio.TwilioSmsProvider` sends real messages through Twilio.

Switch providers by setting the `PHONE_VERIFICATION_SMS_BACKEND` environment variable, e.g.

```env
PHONE_VERIFICATION_SMS_BACKEND=phone_verification.sms.twilio.TwilioSmsProvider
```

### Twilio Configuration

When using Twilio, provide credentials and the sending number via environment variables:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890
```

These values are read automatically through `PHONE_VERIFICATION_TWILIO` settings. Without them the provider raises `ImproperlyConfigured`.
