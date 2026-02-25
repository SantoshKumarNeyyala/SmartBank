from models.user_model import UserModel

def test_register_get(client):
    res = client.get("/register")
    assert res.status_code == 200

def test_login_get(client):
    res = client.get("/login")
    assert res.status_code == 200

def test_login_post_success(client, mocker):
    # fake user tuple (id, full_name, email, password_hash, failed_attempts, is_locked, role)
    fake_user = (1, "Test User", "test@gmail.com", b"$2b$12$fakehash", 0, 0, "user")

    mocker.patch.object(UserModel, "get_user_by_email", return_value=fake_user)

    # mock bcrypt check to True
    from utils.security import bcrypt
    mocker.patch.object(bcrypt, "check_password_hash", return_value=True)

    # mock DB update connections inside login route
    from database.connection import DatabaseConnection
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()
    mock_conn.cursor.return_value = mock_cursor
    mocker.patch.object(DatabaseConnection, "get_connection", return_value=mock_conn)

    res = client.post("/login", data={"email":"test@gmail.com", "password":"123"}, follow_redirects=False)
    assert res.status_code in (302, 303)  # redirect to dashboard