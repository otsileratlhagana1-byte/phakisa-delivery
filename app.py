import os, json, sqlite3, uuid
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, 'phakisa.db')
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key')


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    c = db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT,
      email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS businesses(
      id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL, name TEXT NOT NULL,
      category TEXT, address TEXT, phone TEXT, description TEXT, lat REAL, lon REAL,
      verified INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS products(
      id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER NOT NULL,
      name TEXT NOT NULL, price REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS orders(
      id INTEGER PRIMARY KEY AUTOINCREMENT, order_no TEXT UNIQUE NOT NULL,
      customer_id INTEGER NOT NULL, business_id INTEGER NOT NULL, driver_id INTEGER,
      delivery_address TEXT NOT NULL, subtotal REAL NOT NULL, delivery_fee REAL NOT NULL,
      total REAL NOT NULL, payment_method TEXT, status TEXT DEFAULT 'Placed', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS order_items(
      id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
      product_id INTEGER NOT NULL, name TEXT NOT NULL, price REAL NOT NULL, qty INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS driver_locations(
      driver_id INTEGER PRIMARY KEY, lat REAL NOT NULL, lon REAL NOT NULL,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS ratings(
      id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER UNIQUE NOT NULL,
      driver_id INTEGER NOT NULL, customer_id INTEGER NOT NULL, stars INTEGER NOT NULL, comment TEXT
    );
    ''')
    # Demo accounts
    demos = [
      ('Admin', '0000000000', 'admin@phakisa.co.za', 'admin123', 'admin'),
      ('Demo Driver', '0000000001', 'driver@phakisa.co.za', 'driver123', 'driver')
    ]
    for name, phone, email, pw, role in demos:
        if not c.execute('SELECT 1 FROM users WHERE email=?', (email,)).fetchone():
            c.execute('INSERT INTO users(name,phone,email,password,role) VALUES(?,?,?,?,?)',
                      (name, phone, email, generate_password_hash(pw), role))
    c.commit(); c.close()


init_db()


def user():
    uid = session.get('user_id')
    if not uid:
        return None
    c = db(); u = c.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone(); c.close()
    return u


@app.context_processor
def inject_user():
    return {'current_user': user()}


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not user():
            flash('Please log in first.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            u = user()
            if not u:
                return redirect(url_for('login'))
            if u['role'] not in roles:
                flash('You do not have permission for that page.')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return deco


@app.route('/')
def index():
    c = db(); businesses = c.execute('SELECT * FROM businesses WHERE verified=1 ORDER BY id DESC').fetchall(); c.close()
    return render_template('index.html', businesses=businesses)


@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name=request.form.get('name','').strip(); phone=request.form.get('phone','').strip(); email=request.form.get('email','').strip().lower(); pw=request.form.get('password',''); role=request.form.get('role','customer')
        if role not in ('customer','business'): role='customer'
        try:
            c=db(); c.execute('INSERT INTO users(name,phone,email,password,role) VALUES(?,?,?,?,?)',(name,phone,email,generate_password_hash(pw),role)); c.commit(); c.close()
            flash('Registration successful. Please log in.'); return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('That email is already registered.')
    return render_template('register.html')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form.get('email','').strip().lower(); pw=request.form.get('password','')
        c=db(); u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone(); c.close()
        if u and check_password_hash(u['password'],pw):
            session['user_id']=u['id']; return redirect(url_for('dashboard'))
        flash('Invalid email or password.')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    u=user()
    if u['role']=='admin': return redirect(url_for('admin'))
    if u['role']=='driver': return redirect(url_for('driver'))
    if u['role']=='business': return redirect(url_for('business'))
    c=db(); orders=c.execute('''SELECT o.*, b.name business_name FROM orders o JOIN businesses b ON b.id=o.business_id WHERE o.customer_id=? ORDER BY o.id DESC''',(u['id'],)).fetchall(); c.close()
    return render_template('customer_dashboard.html',orders=orders)


@app.route('/business/register', methods=['GET','POST'])
@login_required
@role_required('business')
def business_register():
    u=user(); c=db(); b=c.execute('SELECT * FROM businesses WHERE owner_id=?',(u['id'],)).fetchone()
    if request.method=='POST':
        vals=(request.form.get('name',''),request.form.get('category',''),request.form.get('address',''),request.form.get('phone',''),request.form.get('description',''))
        try: lat=float(request.form.get('lat') or 0) or None
        except: lat=None
        try: lon=float(request.form.get('lon') or 0) or None
        except: lon=None
        if b:
            c.execute('UPDATE businesses SET name=?,category=?,address=?,phone=?,description=?,lat=?,lon=? WHERE id=?',(*vals,lat,lon,b['id']))
        else:
            c.execute('INSERT INTO businesses(owner_id,name,category,address,phone,description,lat,lon) VALUES(?,?,?,?,?,?,?,?)',(u['id'],*vals,lat,lon))
        c.commit(); c.close(); flash('Business saved. Admin verification may be required.'); return redirect(url_for('business'))
    c.close(); return render_template('business_register.html',business=b)


@app.route('/business')
@login_required
@role_required('business')
def business():
    u=user(); c=db(); b=c.execute('SELECT * FROM businesses WHERE owner_id=?',(u['id'],)).fetchone()
    if not b:
        c.close(); return redirect(url_for('business_register'))
    products=c.execute('SELECT * FROM products WHERE business_id=? ORDER BY id DESC',(b['id'],)).fetchall()
    orders=c.execute('''SELECT o.*,u.name customer_name FROM orders o JOIN users u ON u.id=o.customer_id WHERE o.business_id=? ORDER BY o.id DESC''',(b['id'],)).fetchall(); c.close()
    return render_template('business.html',business=b,products=products,orders=orders)


@app.route('/business/product', methods=['POST'])
@login_required
@role_required('business')
def business_product():
    u=user(); c=db(); b=c.execute('SELECT * FROM businesses WHERE owner_id=?',(u['id'],)).fetchone()
    if not b: c.close(); return redirect(url_for('business_register'))
    try: price=float(request.form.get('price','0'))
    except: price=0
    c.execute('INSERT INTO products(business_id,name,price) VALUES(?,?,?)',(b['id'],request.form.get('name',''),price)); c.commit(); c.close(); return redirect(url_for('business'))


@app.route('/shop/<int:business_id>')
def shop(business_id):
    c=db(); b=c.execute('SELECT * FROM businesses WHERE id=? AND verified=1',(business_id,)).fetchone(); products=c.execute('SELECT * FROM products WHERE business_id=?',(business_id,)).fetchall() if b else []; c.close()
    if not b: return 'Business not found or not verified',404
    return render_template('shop.html',business=b,products=products)


@app.route('/order', methods=['POST'])
@login_required
def order():
    if user()['role']!='customer': flash('Customer account required.'); return redirect(url_for('dashboard'))
    try: items=json.loads(request.form.get('items','[]'))
    except: items=[]
    business_id=int(request.form.get('business_id','0')); address=request.form.get('address','').strip(); payment=request.form.get('payment_method','Cash on Delivery')
    c=db(); valid=[]; subtotal=0
    for item in items:
        p=c.execute('SELECT * FROM products WHERE id=? AND business_id=?',(int(item.get('id')),business_id)).fetchone()
        qty=max(1,int(item.get('qty',1))) if p else 0
        if p and qty: valid.append((p,qty)); subtotal += p['price']*qty
    if not valid: c.close(); flash('Your cart is empty.'); return redirect(url_for('shop',business_id=business_id))
    fee=15.0 if subtotal>=200 else 25.0; total=subtotal+fee; no='PHK-'+uuid.uuid4().hex[:8].upper()
    c.execute('INSERT INTO orders(order_no,customer_id,business_id,delivery_address,subtotal,delivery_fee,total,payment_method) VALUES(?,?,?,?,?,?,?,?)',(no,user()['id'],business_id,address,subtotal,fee,total,payment))
    oid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
    for p,qty in valid: c.execute('INSERT INTO order_items(order_id,product_id,name,price,qty) VALUES(?,?,?,?,?)',(oid,p['id'],p['name'],p['price'],qty))
    c.commit(); c.close(); return redirect(url_for('track',order_no=no))


@app.route('/track/<order_no>')
@login_required
def track(order_no):
    c=db(); o=c.execute('''SELECT o.*, b.name business_name, u.name driver_name FROM orders o JOIN businesses b ON b.id=o.business_id LEFT JOIN users u ON u.id=o.driver_id WHERE o.order_no=?''',(order_no,)).fetchone()
    rating=c.execute('SELECT * FROM ratings WHERE order_id=?',(o['id'],)).fetchone() if o else None; c.close()
    if not o: return 'Order not found',404
    if user()['role']=='customer' and o['customer_id']!=user()['id']: return 'Forbidden',403
    return render_template('track.html',order=o,rating=rating)


@app.route('/api/order/<order_no>')
def api_order(order_no):
    c=db(); o=c.execute('SELECT * FROM orders WHERE order_no=?',(order_no,)).fetchone(); loc=None
    if o and o['driver_id']: loc=c.execute('SELECT lat,lon FROM driver_locations WHERE driver_id=?',(o['driver_id'],)).fetchone()
    c.close()
    if not o: return jsonify({'error':'not found'}),404
    return jsonify({'order_no':o['order_no'],'status':o['status'],'driver_lat':loc['lat'] if loc else None,'driver_lon':loc['lon'] if loc else None})


@app.route('/driver')
@login_required
@role_required('driver')
def driver():
    c=db(); orders=c.execute('''SELECT o.*,b.name business_name FROM orders o JOIN businesses b ON b.id=o.business_id WHERE o.status NOT IN ('Delivered','Cancelled') ORDER BY o.id DESC''').fetchall(); c.close(); return render_template('driver.html',orders=orders)


@app.route('/driver/update/<int:order_id>',methods=['POST'])
@login_required
@role_required('driver')
def driver_update(order_id):
    status=request.form.get('status','Accepted'); c=db(); c.execute('UPDATE orders SET status=?,driver_id=? WHERE id=?',(status,user()['id'],order_id)); c.commit(); c.close(); return redirect(url_for('driver'))


@app.route('/driver/location',methods=['POST'])
@login_required
@role_required('driver')
def driver_location():
    data=request.get_json(silent=True) or {}
    try: lat=float(data['lat']); lon=float(data['lon'])
    except: return jsonify({'error':'invalid coordinates'}),400
    c=db(); c.execute('''INSERT INTO driver_locations(driver_id,lat,lon,updated_at) VALUES(?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(driver_id) DO UPDATE SET lat=excluded.lat,lon=excluded.lon,updated_at=CURRENT_TIMESTAMP''',(user()['id'],lat,lon)); c.commit(); c.close(); return jsonify({'ok':True})


@app.route('/rate/<int:order_id>',methods=['POST'])
@login_required
@role_required('customer')
def rate(order_id):
    stars=max(1,min(5,int(request.form.get('stars',5)))); comment=request.form.get('comment',''); c=db(); o=c.execute('SELECT * FROM orders WHERE id=? AND customer_id=?',(order_id,user()['id'])).fetchone()
    if not o or not o['driver_id']: c.close(); return 'Invalid order',400
    c.execute('INSERT OR REPLACE INTO ratings(order_id,driver_id,customer_id,stars,comment) VALUES(?,?,?,?,?)',(order_id,o['driver_id'],user()['id'],stars,comment)); c.commit(); c.close(); return redirect(url_for('track',order_no=o['order_no']))


@app.route('/admin')
@login_required
@role_required('admin')
def admin():
    c=db(); businesses=c.execute('SELECT b.*,u.email owner_email FROM businesses b JOIN users u ON u.id=b.owner_id ORDER BY b.id DESC').fetchall(); orders=c.execute('''SELECT o.*,b.name business_name,u.name customer_name FROM orders o JOIN businesses b ON b.id=o.business_id JOIN users u ON u.id=o.customer_id ORDER BY o.id DESC''').fetchall(); c.close(); return render_template('admin.html',businesses=businesses,orders=orders)


@app.route('/admin/verify/<int:business_id>',methods=['POST'])
@login_required
@role_required('admin')
def verify_business(business_id):
    c=db(); c.execute('UPDATE businesses SET verified=1 WHERE id=?',(business_id,)); c.commit(); c.close(); return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=True)
