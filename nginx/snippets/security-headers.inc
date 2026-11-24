# Repeated in every location that sets its own headers (nginx drops inherited add_header otherwise).
# Google Tag Manager + GA4 hosts as documented by Google. GTM "Custom HTML" tags would additionally need a nonce.
add_header Content-Security-Policy "default-src 'self'; img-src 'self' data: https://*.google-analytics.com https://*.googletagmanager.com; style-src 'self'; script-src 'self' https://*.googletagmanager.com; font-src 'self'; connect-src 'self' https://*.google-analytics.com https://*.analytics.google.com https://*.googletagmanager.com; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), interest-cohort=()" always;
add_header X-Frame-Options "DENY" always;
