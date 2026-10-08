# API & Endpoint Notes

## Auth and Session

- `POST /login/`: Initiates OTP login for registered users.
- `POST /verify-otp-login/`: Verifies OTP, enforces OTP expiry and login-attempt throttling.
- `POST /verify-otp/`: Verifies OTP during registration.

## Location APIs

- `GET /get-villages/?pincode=<6_digits>`
  - Trims surrounding whitespace and returns the matching villages array.
- `GET /get-location/?pincode=<6_digits>`
  - Returns:
    - `success: true`
    - `state`
    - `district`
    - `mandal`
    - `villages`
    - `village_locations`, mapping each village to its district and mandal
  - Returns HTTP 400 for an invalid pincode and HTTP 404 when no mapping exists.
  - Lookup uses the bundled Telangana dataset, with imported database mappings as a fallback.

## Booking APIs (HTML endpoints)

- `POST /book-labor/<labor_id>/`
- `POST /book-tractor/<tractor_id>/`
- `POST /book-tool/<tool_id>/`
- `POST /request-lease/<land_id>/`
- `POST /book-shop/<shop_id>/`

These endpoints enforce session login + role checks and create normalized `Order` records for analytics.

## Versioning Guidance

Current endpoints are server-rendered and unversioned. If external/mobile clients are introduced, adopt `/api/v1/...` namespace and schema contracts.
