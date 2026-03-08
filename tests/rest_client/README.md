# VS Code REST Client quickstart

Use these files with the **REST Client** extension (`humao.rest-client`).

## Files
- `auth.rest`: session-cookie and bearer-token login flows
- `protected_endpoints.rest`: sample protected endpoint calls using bearer auth

## How auth is handled in this API
- Session flow:
  1. `POST /api/auth/login/` sets `sessionid` and `csrftoken` cookies.
  2. Subsequent requests can authenticate via that `sessionid` cookie.
  3. In REST Client, cookie jar support will send cookies automatically after login.
- Token flow:
  1. `POST /api/auth/token/` returns `access_token`.
  2. Send `Authorization: Bearer <access_token>` to protected endpoints.

The backend currently authorizes protected routes via bearer token first, then session cookie.

## Usage
1. Replace `@username` and `@password` values.
2. Start API server (example): `uvicorn main:app --reload`.
3. Run requests in order from each `.rest` file.

If you need a quick protected check, run `tokenLogin` then `GET /api/auth/me/` with bearer auth.
