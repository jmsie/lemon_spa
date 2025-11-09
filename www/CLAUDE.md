# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based spa/therapy appointment booking system called "Lemon Spa". The application allows therapists to manage their schedules, treatments, and appointments, while clients can book appointments and provide feedback via questionnaires. The system uses phone number authentication with SMS verification.

## Development Commands

### Environment Setup
- Copy `.env.example` to `.env` and configure environment variables
- Install dependencies: `pip install -r requirements.txt`
- Run migrations: `python manage.py migrate`
- Create superuser: `python manage.py createsuperuser`
- Collect static files: `python manage.py collectstatic`

### Running the Application
- Development server: `python manage.py runserver`
- With Docker: `docker-compose up`
- Production with Docker: `docker-compose -f docker-compose.prod.yml up`

### Testing
- Run all tests: `python manage.py test`
- Run tests for a specific app: `python manage.py test <app_name>`
- Run a specific test file: `python manage.py test <app_name>.tests.TestClassName`
- Example: `python manage.py test therapist_panel.tests.TherapistOnboardingFlowTests`

### Database
- Make migrations: `python manage.py makemigrations`
- Apply migrations: `python manage.py migrate`
- Shell access: `python manage.py shell`

### Other Commands
- Django admin: Access at `/admin/` after starting the server
- Management shell: `python manage.py shell`

## Architecture

### Custom User Model
- **Custom user model**: `accounts.AccountUser` (extends `AbstractUser`)
- **Phone-based authentication**: Users authenticate with phone numbers (E.164 format)
- **Dual authentication backends**: `PhoneNumberBackend` and standard `ModelBackend`
- Phone numbers are normalized using `phone_verification.utils.normalize_phone_number`

### Core Domain Models

#### Therapist System (`therapist_panel` app)
- **Therapist**: Main therapist profile linked to `AccountUser` with timezone support
- **TherapistTreatment**: Services offered by therapists with duration, price, and preparation time
- Therapist API is organized into sub-modules (serializers, views, urls) by feature:
  - `registration`: Therapist onboarding
  - `therapists`: Therapist profile management
  - `treatments`: Treatment/service management
  - `working_hours`: Working hours configuration
  - `time_off`: Time off periods

#### Scheduling System (`scheduling` app)
- **TherapistWorkingHoursSeries**: Recurring weekly working hour patterns
- **TherapistWorkingHours**: Individual working hour blocks (can be generated from series or standalone)
- **TherapistTimeOffSeries**: Recurring time off patterns (daily or weekly)
- **TherapistTimeOff**: Individual time off periods
- All times stored in UTC in the database; converted to therapist's timezone for display
- Use `scheduling.utils.to_utc()` and `scheduling.utils.from_utc()` for timezone conversions

#### Appointments (`appointments` app)
- **Appointment**: Bookings between therapist and customer
- Automatically calculates `end_time` from treatment duration + preparation time
- **TherapistSmsNotificationLog**: Tracks SMS notifications sent to therapists
- **AppointmentQuestionnaireLog**: Tracks questionnaire invitation SMS with uniqueness constraint

#### Phone Verification (`phone_verification` app)
- **PhoneVerification**: Stores hashed verification codes with expiration and rate limiting
- **PhoneVerificationService**: Orchestrates code generation, validation, and SMS sending
- Configurable via `PHONE_VERIFICATION` settings dict
- SMS provider architecture: pluggable backends (Twilio and Dummy for testing)
- Use `PHONE_VERIFICATION_SMS_BACKEND` to select provider

#### Questionnaires (`questionnaires` app)
- **Questionnaire**: Post-service feedback (1-5 star rating) linked to appointments
- Chinese language labels in model fields

### Application Structure

The project follows Django's standard app structure:

- `accounts/`: User authentication and account management
- `therapist_panel/`: Therapist profiles, treatments, and therapist-facing views
- `client_dashboard/`: Client-facing dashboard views
- `appointments/`: Appointment booking and management
- `scheduling/`: Working hours and time-off management
- `phone_verification/`: SMS verification system
- `questionnaires/`: Post-service feedback forms
- `lemon_spa/`: Django project settings and root URL configuration

### API Organization

REST APIs are centralized at `/api/` with namespace routing:
- `/api/therapist_panel/` - Therapist management endpoints
- `/api/appointments/` - Appointment endpoints
- `/api/questionnaires/` - Questionnaire endpoints
- `/api/phone_verification/` - SMS verification endpoints

API URLs are configured in `lemon_spa/api/urls.py` which imports from each app's API module.

### Settings Architecture

`lemon_spa/settings.py` implements custom environment variable loading:
- Custom `.env` file parser (`_load_env_file`)
- Helper functions: `_env()`, `_env_bool()`, `_env_list()`
- Database URL parsing supports PostgreSQL
- Timezone defaults to `Asia/Taipei`
- Security headers configurable via environment variables

### Testing Patterns

Tests use Django's `TestCase` and DRF's `APITestCase`:
- Set up test data in `setUp()` method
- Use `reverse()` for URL generation
- Role-based access control tested via session variable `SESSION_ACTIVE_ROLE_KEY`
- Phone verification tests in `phone_verification/tests/`
- API tests verify response structure and status codes

## Important Conventions

### Phone Numbers
- Always normalize phone numbers using `phone_verification.utils.normalize_phone_number`
- Store in E.164 format (e.g., `+886900000001`)
- Handle `InvalidPhoneNumber` exception appropriately

### Timezones
- Database stores all datetimes in UTC
- Therapists have a `timezone` field (IANA timezone identifier)
- Convert to local time for display using `scheduling.utils.from_utc()`
- Convert from local to UTC using `scheduling.utils.to_utc()`
- Default timezone: `Asia/Taipei`

### Model Patterns
- UUIDs used as external identifiers (not primary keys)
- `created_at` and `updated_at` timestamps on most models
- Soft deletes via `is_active` or `is_cancelled` flags
- Use `select_for_update()` for concurrent operations (e.g., phone verification)

### API Patterns
- DRF serializers and viewsets used throughout
- API responses follow REST conventions
- Serializers organized by feature area in larger apps

### Code Organization
- Type hints used extensively (`from __future__ import annotations`)
- Service layer pattern for business logic (e.g., `PhoneVerificationService`)
- Models kept lean; business logic in services or managers
- Custom managers extend functionality (e.g., `AccountUserManager`)

## Common Development Workflows

### Adding a New Therapist Treatment
1. Create via Django admin or API endpoint
2. Treatment includes: name, duration_minutes, price, preparation_minutes
3. Appointments automatically calculate end_time based on treatment duration + prep time

### Working with Phone Verification
1. Request code: `PhoneVerificationService().request_code(phone_number)`
2. Verify code: `PhoneVerificationService().verify_code(phone_number, code)`
3. Check status: `PhoneVerificationService().get_status(phone_number)`
4. Rate limiting and max attempts enforced by service layer

### Managing Therapist Schedules
1. Create recurring series (`TherapistWorkingHoursSeries`)
2. Generate occurrences (`TherapistWorkingHours`) with `is_generated=True`
3. Mark exceptions with `is_skipped=True` rather than deleting
4. Similar pattern for time-off management

### Role-Based Access
- User roles stored in session: `request.session[SESSION_ACTIVE_ROLE_KEY]`
- Available roles defined in `accounts.constants`: `ROLE_THERAPIST`, etc.
- Use decorators from `accounts.decorators` for view protection

## Database

- Development: SQLite (default) or PostgreSQL via `POSTGRES_*` env vars
- Production: PostgreSQL (configured via `DATABASE_URL` or `POSTGRES_*` variables)
- Important: Appointment table has typo in `db_table`: `"appoinments"` (not "appointments")

## Dependencies

Key dependencies:
- Django 5.x
- Django REST Framework 3.15+
- psycopg 3.x (PostgreSQL adapter)
- phonenumbers (phone number validation)
- twilio (SMS provider)
- gunicorn (production WSGI server)
