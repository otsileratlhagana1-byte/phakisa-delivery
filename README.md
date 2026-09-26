# Phakisa Delivery v2

## Included
Customer accounts, business registration/verification, product menu, cart, delivery-fee calculation, order tracking, driver dashboard, browser GPS sharing, live driver marker on Leaflet/OpenStreetMap, ratings, admin dashboard and Render deployment.

## Pydroid 3
pip install -r requirements.txt
python app.py
Open http://127.0.0.1:5000

Admin: admin@phakisa.co.za / admin123
Driver: driver@phakisa.co.za / driver123

## Render
Build: pip install -r requirements.txt
Start: gunicorn app:app
Set SECRET_KEY.

## Production
Connect a payment provider (PayFast/Stripe/etc.) using real merchant credentials; add HTTPS, persistent PostgreSQL storage, push notifications and production driver authentication before launch.
