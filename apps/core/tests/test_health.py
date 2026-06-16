import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_endpoint_returns_ok(client):
    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "realityng-backend",
        "version": "0.1.0",
    }
    assert "X-Request-ID" in response

