import threading
import time
import csv
import argparse
import shutil
from datetime import datetime
from sqlalchemy import Integer
from flask import Flask, request, jsonify
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Base, Order, Product, Customer

parser = argparse.ArgumentParser(description="Product Assessment REST API")
parser.add_argument('--db', type=str, default='product_assessment.db', help='SQLite DB filename')
parser.add_argument('--csv', type=str, default='input.csv', help='Input CSV filename')
args, unknown = parser.parse_known_args()

DB_FILE = args.db
CSV_FILE = args.csv

db_lock = threading.Lock()

engine = create_engine(
    f'sqlite:///{DB_FILE}',
    connect_args={'check_same_thread': False, 'timeout': 30}
)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def revenue_expr():
    return (Order.quantity * Order.unit_price) - Order.discount + Order.shipping_cost

def backup_db():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"{DB_FILE.rsplit('.', 1)[0]}_backup_{timestamp}.db"
    try:
        shutil.copy(DB_FILE, backup_file)
        print(f"Database backup created: {backup_file}")
    except Exception as e:
        print(f"Backup failed: {e}")

def safe_int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return None

def safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def update_db_in_thread():
    while True:
        backup_db()
        time.sleep(60)
        update_db_from_csv

def update_db_from_csv():
        with db_lock:
            session = Session()
            with open(CSV_FILE, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    cust_id = row['Customer ID']
                    prod_id = row['Product ID']
                    order_id = row['Order ID']

                    quantity = safe_int(row.get('Quantity Sold'))
                    unit_price = safe_float(row.get('Unit Price'))
                    discount = safe_float(row.get('Discount'))
                    shipping_cost = safe_float(row.get('Shipping Cost'))
                    payment_method = row.get('Payment Method', '')

                    if None in (quantity, unit_price, discount, shipping_cost):
                        continue

                    customer = session.query(Customer).filter_by(id=cust_id).first()
                    if not customer:
                        customer = Customer(
                            id=cust_id,
                            name=row['Customer Name'],
                            email=row['Customer Email'],
                            address=row['Customer Address'],
                            other_details=""
                        )
                        session.add(customer)
                    else:
                        if customer.name != row['Customer Name']:
                            customer.name = row['Customer Name']
                        if customer.email != row['Customer Email']:
                            customer.email = row['Customer Email']
                        if customer.address != row['Customer Address']:
                            customer.address = row['Customer Address']

                    product = session.query(Product).filter_by(id=prod_id).first()
                    if not product:
                        product = Product(
                            id=prod_id,
                            name=row['Product Name'],
                            category=row['Category']
                        )
                        session.add(product)
                    else:
                        if product.name != row['Product Name']:
                            product.name = row['Product Name']
                        if product.category != row['Category']:
                            product.category = row['Category']

                    order = session.query(Order).filter_by(id=order_id).first()
                    if not order:
                        order = Order(
                            id=order_id,
                            customer_id=cust_id,
                            product_id=prod_id,
                            region=row['Region'],
                            date=row['Date of Sale'],
                            quantity=quantity,
                            unit_price=unit_price,
                            discount=discount,
                            shipping_cost=shipping_cost,
                            payment_method=payment_method
                        )
                        session.add(order)
                    else:  # If you want to update, keep this block. If you want to skip, do nothing.
                        if order.customer_id != cust_id:
                            order.customer_id = cust_id
                        if order.product_id != prod_id:
                            order.product_id = prod_id
                        if order.region != row['Region']:
                            order.region = row['Region']
                        if order.date != row['Date of Sale']:
                            order.date = row['Date of Sale']
                        if order.quantity != quantity:
                            order.quantity = quantity
                        if order.unit_price != unit_price:
                            order.unit_price = unit_price
                        if order.discount != discount:
                            order.discount = discount
                        if order.shipping_cost != shipping_cost:
                            order.shipping_cost = shipping_cost
                        if order.payment_method != payment_method:
                            order.payment_method = payment_method

                session.commit()
            session.close()




app = Flask(__name__)



@app.route('/total_revenue', methods=['GET'])
def total_revenue():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400
    session = Session()
    total = session.query(func.sum(revenue_expr())).filter(
        Order.date >= start_date, Order.date <= end_date
    ).scalar() or 0.0
    session.close()
    return jsonify({'total_revenue': total})

@app.route('/total_revenue_by_product', methods=['GET'])
def total_revenue_by_product():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400
    session = Session()
    results = session.query(
        Order.product_id,
        func.sum(revenue_expr())
    ).filter(
        Order.date >= start_date, Order.date <= end_date
    ).group_by(Order.product_id).all()
    data = [{'product_id': pid, 'total_revenue': rev} for pid, rev in results]
    session.close()
    return jsonify(data)

@app.route('/total_revenue_by_category', methods=['GET'])
def total_revenue_by_category():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400
    session = Session()
    results = session.query(
        Product.category,
        func.sum(revenue_expr())
    ).join(Product, Product.id == Order.product_id).filter(
        Order.date >= start_date, Order.date <= end_date
    ).group_by(Product.category).all()
    data = [{'category': cat, 'total_revenue': rev} for cat, rev in results]
    session.close()
    return jsonify(data)

@app.route('/total_revenue_by_region', methods=['GET'])
def total_revenue_by_region():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400
    session = Session()
    results = session.query(
        Order.region,
        func.sum(revenue_expr())
    ).filter(
        Order.date >= start_date, Order.date <= end_date
    ).group_by(Order.region).all()
    data = [{'region': region, 'total_revenue': rev} for region, rev in results]
    session.close()
    return jsonify(data)

@app.route('/revenue_trends', methods=['GET'])
def revenue_trends():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    interval = request.args.get('interval', 'monthly')  # monthly, quarterly, yearly
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400
    session = Session()
    if interval == 'monthly':
        results = session.query(
            func.substr(Order.date, 1, 7).label('period'),
            func.sum(revenue_expr())
        ).filter(
            Order.date >= start_date, Order.date <= end_date
        ).group_by('period').order_by('period').all()
    elif interval == 'quarterly':
        results = session.query(
            func.substr(Order.date, 1, 4).label('year'),
            ((func.substr(Order.date, 6, 2).cast(Integer) - 1) / 3 + 1).label('quarter'),
            func.sum(revenue_expr())
        ).filter(
            Order.date >= start_date, Order.date <= end_date
        ).group_by('year', 'quarter').order_by('year', 'quarter').all()
        results = [(
            f"{year}-Q{int(quarter)}", rev
        ) for year, quarter, rev in results]
    elif interval == 'yearly':
        results = session.query(
            func.substr(Order.date, 1, 4).label('year'),
            func.sum(revenue_expr())
        ).filter(
            Order.date >= start_date, Order.date <= end_date
        ).group_by('year').order_by('year').all()
    else:
        session.close()
        return jsonify({'error': 'Invalid interval'}), 400

    if interval == 'quarterly':
        data = [{'period': period, 'total_revenue': rev} for period, rev in results]
    else:
        data = [{'period': period, 'total_revenue': rev} for period, rev in results]
    session.close()
    return jsonify(data)

if __name__ == '__main__':
    update_db_from_csv()
    threading.Thread(target=update_db_in_thread, daemon=True).start()
    app.run(debug=True, port=8080)