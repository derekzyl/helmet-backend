EMAIL_TEMPLATES = {
    "verify_email": """
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; line-height: 1.5;">
  <h2>Verify your email</h2>
  <p>Hi {{ name }},</p>
  <p>Your verification code is:</p>
  <p style="font-size: 24px; font-weight: bold; letter-spacing: 4px;">{{ otp }}</p>
  <p>This code expires in {{ expiry_hours }} hour(s).</p>
  <p>— {{ website_name }}</p>
</body>
</html>
""",
    "reset_password": """
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; line-height: 1.5;">
  <h2>Reset your password</h2>
  <p>Hi {{ name }},</p>
  <p>Your password reset code is:</p>
  <p style="font-size: 24px; font-weight: bold; letter-spacing: 4px;">{{ otp }}</p>
  <p>This code expires in {{ expiry_hours }} hour(s).</p>
</body>
</html>
""",
    "password_change": """
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; line-height: 1.5;">
  <h2>Password changed</h2>
  <p>Hi {{ name }},</p>
  <p>Your password for {{ email }} was changed successfully.</p>
  <p>If you did not do this, contact {{ support_email }}.</p>
</body>
</html>
""",
    "welcome": """
<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; line-height: 1.5;">
  <h2>Welcome to {{ app_name }}</h2>
  <p>Hi {{ name }},</p>
  <p>Your account is ready. <a href="{{ login_link }}">Sign in</a> to get started.</p>
</body>
</html>
""",
}
