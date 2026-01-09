import pytest
from app.core.config import config


@pytest.mark.asyncio
async def test_list_admin_subscription_plans(async_client):
    resp = await async_client.get(
		"/api/admin/subscription-plans",
		headers={"X-Admin-Token": config.ADMIN_TOKEN}
	)
    assert resp.status_code == 200

    data = resp.json()
    assert "plans" in data
    assert isinstance(data["plans"], list)

    expected_fields = {
        "tier",
        "name",
        "monthly_cost",
        "fixed_cost",
        "credits_included",
        "bonus_credits",
        "multiplier",
        "purchase_rate",
        "active",
        "users_count",
        "created_at",
        "updated_at",
    }
    if data["plans"]:
        plan = data["plans"][0]
        # має бути рівно 12 полів
        assert len(plan) == 12
        # усі очікувані поля присутні
        assert expected_fields.issubset(plan.keys())

        # (!) перевірити значення user_count
    else:
        pytest.skip("No plans yet.")
