import pytest

from app.core.config import config


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


@pytest.mark.asyncio
async def test_list_user_transactions(async_client):
	resp = await async_client.get(
		"/api/v1/transactions",
		headers={"Authorization": f"Bearer {config.USER_TOKEN_BEARER}"}
	)

	assert resp.status_code == 200
	data = resp.json()

	expected_fields = {
		"total",
		"limit",
		"offset",
		"transactions"
	}

	# усі очікувані поля присутні
	assert expected_fields.issubset(data.keys())

	# перевіряємо, що є transactions - list
	assert isinstance(data["transactions"], list)

	if len(data["transactions"]) > 0:
		transaction = data["transactions"][0]  # 1 txn

		# має бути >= 7 полів
		assert len(transaction) >= 7

		expected_fields_transaction = {
			"id",
			"type",
			"date",
			"credits",
			"balance_after",
			"description",
			"operation_id"
		}

		# усі очікувані поля присутні
		assert expected_fields_transaction.issubset(transaction.keys())
