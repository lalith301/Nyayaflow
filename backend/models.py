"""
NyayaFlow - Database Models
SQLite via Flask-SQLAlchemy

Tables:
  User         — auth + token balance
  ChatMessage  — chat history per user
  Transaction  — token purchase history
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name          = db.Column(db.String(100), nullable=False)
    tokens        = db.Column(db.Integer, default=100, nullable=False)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    messages      = db.relationship("ChatMessage", backref="user", lazy=True, cascade="all,delete")
    transactions  = db.relationship("Transaction", backref="user", lazy=True, cascade="all,delete")

    def to_dict(self):
        return {
            "id":         self.id,
            "email":      self.email,
            "name":       self.name,
            "tokens":     self.tokens,
            "created_at": self.created_at.isoformat(),
        }


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    role        = db.Column(db.String(20), nullable=False)   # 'user' | 'assistant'
    content     = db.Column(db.Text, nullable=False)
    sources     = db.Column(db.Text, default="[]")           # JSON string
    used_agent  = db.Column(db.Boolean, default=False)
    law_fetched = db.Column(db.String(200), default=None)
    tokens_used = db.Column(db.Integer, default=0)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        import json
        return {
            "id":          self.id,
            "role":        self.role,
            "content":     self.content,
            "sources":     json.loads(self.sources or "[]"),
            "used_agent":  self.used_agent,
            "law_fetched": self.law_fetched,
            "tokens_used": self.tokens_used,
            "created_at":  self.created_at.isoformat(),
        }


class Transaction(db.Model):
    __tablename__ = "transactions"

    id                 = db.Column(db.Integer, primary_key=True)
    user_id            = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    razorpay_order_id  = db.Column(db.String(100), unique=True, nullable=False)
    razorpay_payment_id= db.Column(db.String(100), nullable=True)
    amount_paise       = db.Column(db.Integer, nullable=False)   # amount in paise (₹1 = 100 paise)
    tokens_purchased   = db.Column(db.Integer, nullable=False)
    status             = db.Column(db.String(20), default="created")  # created | paid | failed
    created_at         = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id":                  self.id,
            "razorpay_order_id":   self.razorpay_order_id,
            "razorpay_payment_id": self.razorpay_payment_id,
            "amount_paise":        self.amount_paise,
            "amount_rupees":       self.amount_paise / 100,
            "tokens_purchased":    self.tokens_purchased,
            "status":              self.status,
            "created_at":          self.created_at.isoformat(),
        }