# VS Code REST Client quickstart

Use these files with the **REST Client** extension (`humao.rest-client`).

## Files
- `auth.rest`: browser session-cookie login flow
- `protected_endpoints.rest`: protected GET using a provisioned service token

## How auth is handled in this API
- Session flow:
  1. `POST /api/auth/login/` sets `sessionid` and `csrftoken` cookies.
  2. Subsequent requests can authenticate via that `sessionid` cookie.
  3. In REST Client, cookie jar support will send cookies automatically after login.
- Service token flow:
  1. Staff provision a token in the Service access view.
  2. Send `Authorization: Bearer <access_token>` to protected GET endpoints.

The backend currently authorizes protected routes via bearer token first, then session cookie.

## Usage
1. Replace `@username` and `@password` values.
2. Start API server (example): `uvicorn main:app --reload`.
3. Run requests in order from each `.rest` file.

For a protected machine check, set `SERMON_ARCHIVE_TOKEN` and use
`protected_endpoints.rest`.
