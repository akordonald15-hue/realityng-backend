from django.db import models


class RoleName(models.TextChoices):
    TENANT = "tenant", "Tenant"
    BUYER = "buyer", "Buyer"
    LANDLORD = "landlord", "Landlord"
    AGENT = "agent", "Agent"
    ARTISAN = "artisan", "Artisan"
    INSPECTOR = "inspector", "Inspector"
    ADMIN = "admin", "Admin"
    SUPER_ADMIN = "super_admin", "Super Admin"


class UserRoleStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


AUTO_APPROVED_ROLES = {
    RoleName.TENANT,
    RoleName.BUYER,
    RoleName.LANDLORD,
}

ADMIN_ONLY_ROLES = {
    RoleName.ADMIN,
    RoleName.SUPER_ADMIN,
}

PROFESSIONAL_ROLES = {
    RoleName.AGENT,
    RoleName.ARTISAN,
    RoleName.INSPECTOR,
}
