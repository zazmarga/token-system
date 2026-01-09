import pytest


@pytest.mark.asyncio
async def test_list_available_subscription_plans(async_client):
	resp = await async_client.get("/api/v1/subscription/plans")
	assert resp.status_code == 200

	data = resp.json()
	assert "plans" in data

	# Перевіряємо, що є ключ "plans"
	assert "plans" in data
	assert isinstance(data["plans"], list)

	# Очікувані поля у кожному плані
	expected_fields = {
		"tier",
		"name",
		"monthly_cost",
		"fixed_cost",
		"credits_included",
		"bonus_credits",
		"total_credits",
		"multiplier",
		"purchase_rate",
	}

	if data["plans"]:
		# Перевіряємо 1 план
		plan = data["plans"][0]
		# має бути рівно 9 полів
		assert len(plan) == 9
		# усі очікувані поля присутні
		assert expected_fields.issubset(plan.keys())
		# total_credits бути рівно (credits_included + bonus_credits)
		assert plan["total_credits"] == plan["credits_included"] + plan["bonus_credits"]
	else:
		pytest.skip("No plans yet.")
