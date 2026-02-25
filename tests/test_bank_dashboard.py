from services.account_service import AccountService
from services.bank_service import BankService

def test_dashboard_requires_login(client):
    res = client.get("/dashboard", follow_redirects=False)
    assert res.status_code in (302, 303)

def test_dashboard_ok(auth_session, mocker):
    # mock accounts
    fake_accounts = [
        (10, "SB00000010", "savings", 1000.00),
        (11, "SB00000011", "savings", 500.00),
    ]

    mocker.patch.object(AccountService, "get_user_accounts", return_value=fake_accounts)
    mocker.patch.object(BankService, "get_balance", return_value=1000.00)

    res = auth_session.get("/dashboard")
    assert res.status_code == 200
    assert b"Your Accounts" in res.data