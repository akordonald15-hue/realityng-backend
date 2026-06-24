# RealityNG Backend Authentication and Roles

## API Examples

### Register

```http
POST /api/v1/auth/register/
Content-Type: application/json
```

```json
{
  "email": "ada@example.com",
  "password": "Str0ngPass123!",
  "first_name": "Ada",
  "last_name": "Okafor",
  "phone_number": "+2348010000000"
}
```

### Login

```http
POST /api/v1/auth/login/
Content-Type: application/json
```

```json
{
  "email": "ada@example.com",
  "password": "Str0ngPass123!"
}
```

Response:

```json
{
  "access": "<jwt-access-token>",
  "refresh": "<jwt-refresh-token>",
  "user": {
    "id": "7f49a735-7ce1-4c4a-88fa-bb3a8e0453f7",
    "email": "ada@example.com",
    "roles": []
  }
}
```

### Refresh Token

```http
POST /api/v1/auth/token/refresh/
Content-Type: application/json
```

```json
{
  "refresh": "<jwt-refresh-token>"
}
```

### Current User

```http
GET /api/v1/users/me/
Authorization: Bearer <jwt-access-token>
```

### Update Profile

```http
PATCH /api/v1/users/me/
Authorization: Bearer <jwt-access-token>
Content-Type: application/json
```

```json
{
  "first_name": "Ada",
  "last_name": "Okafor",
  "phone_number": "+2348010000000",
  "profile": {
    "country": "United Kingdom",
    "state": "England",
    "city": "London",
    "bio": "Diaspora buyer researching Nigerian property."
  }
}
```

### Request Role

```http
POST /api/v1/roles/request/
Authorization: Bearer <jwt-access-token>
Content-Type: application/json
```

```json
{
  "role": "agent"
}
```

Professional role response:

```json
{
  "id": "8d76a355-9b89-4a02-8b2c-4510117011b2",
  "role": {
    "name": "agent",
    "approval_required": true
  },
  "status": "pending"
}
```

### Admin Approves Role Request

```http
POST /api/v1/admin/role-requests/{id}/approve/
Authorization: Bearer <admin-jwt-access-token>
Content-Type: application/json
```

```json
{
  "reason": "Business credentials reviewed."
}
```

## Business Rules

1. Email is required and unique.
2. Phone number is optional but unique when present.
3. Suspended users cannot authenticate or use existing JWTs.
4. Tenant and buyer roles are auto-approved.
5. Landlord role is auto-approved while `LANDLORD_ROLE_AUTO_APPROVAL=true`.
6. Agent, artisan, and inspector roles require admin approval.
7. Admin and super admin roles cannot be self-assigned.
8. Users cannot approve or reject their own role requests.
9. Role request and decision actions create audit logs.
