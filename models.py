from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String)
    address = Column(String)
    other_details = Column(String)
    orders = relationship("Order", back_populates="customer")

class Product(Base):
    __tablename__ = 'products'
    id = Column(String, primary_key=True)
    name = Column(String)
    category = Column(String)
    orders = relationship("Order", back_populates="product")

class Order(Base):
    __tablename__ = 'orders'
    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey('customers.id'))
    product_id = Column(String, ForeignKey('products.id'))
    region = Column(String)
    date = Column(String)
    quantity = Column(Integer)
    unit_price = Column(Float)
    discount = Column(Float)
    shipping_cost = Column(Float)
    payment_method = Column(String)

    customer = relationship("Customer", back_populates="orders")
    product = relationship("Product", back_populates="orders")
