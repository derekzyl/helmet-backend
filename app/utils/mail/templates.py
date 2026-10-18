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
    "emergency_alert": """
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f8fafc; padding: 20px;">
  <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
    <div style="background: #dc2626; padding: 18px 24px; color: #ffffff;">
      <h2 style="margin: 0; font-size: 20px; font-weight: bold;">🚨 SMART HELMET SAFETY ALERT</h2>
    </div>
    <div style="padding: 24px;">
      <p style="font-size: 16px; font-weight: bold; color: #dc2626; margin-top: 0;">Event: {{ event_type }} (Severity: {{ severity }})</p>
      <p><strong>Device ID:</strong> {{ device_id }}</p>
      <p><strong>Message:</strong> {{ message }}</p>
      {% if google_maps_url %}
      <p style="margin: 20px 0;">
        <a href="{{ google_maps_url }}" style="display: inline-block; background: #dc2626; color: #ffffff; padding: 12px 20px; border-radius: 6px; text-decoration: none; font-weight: bold;">
          📍 View Incident on Google Maps
        </a>
      </p>
      {% endif %}
      <div style="font-size: 13px; color: #64748b; margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 16px;">
        <p>Timestamp: {{ timestamp }}</p>
        <p>This automated emergency message was dispatched by the Smart Helmet IoT Network.</p>
      </div>
    </div>
  </div>
</body>
</html>
""",
}
