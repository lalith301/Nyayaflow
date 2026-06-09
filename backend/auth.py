"""
NyayaFlow - Auth & Token Routes

POST /api/auth/register   → create account, get JWT + 100 free tokens
POST /api/auth/login      → login, get JWT
GET  /api/auth/me         → get current user info
GET  /api/tokens/balance  → get token balance
GET  /api/tokens/plans    → get available token packages
POST /api/tokens/order    → create Razorpay order
POST /api/tokens/verify   → verify payment + credit tokens
GET  /api/history         → get chat history
"""

import os
import json
import hmac
import hashlib
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)
import bcrypt
import razorpay
from models import db, User, ChatMessage, Transaction

auth_bp = Blueprint("auth", __name__)

FREE_TOKENS     = int(os.getenv("FREE_TOKENS_ON_SIGNUP", 100))
RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

# Token packages
TOKEN_PLANS = [
    { "id":"basic",    "tokens":100,  "price_paise":4900,  "label":"Starter",  "description":"100 queries or 10 PDFs" },
    { "id":"standard", "tokens":300,  "price_paise":9900,  "label":"Standard", "description":"300 queries or 30 PDFs", "popular":True },
    { "id":"pro",      "tokens":1000, "price_paise":24900, "label":"Pro",      "description":"1000 queries or 100 PDFs" },
]

# Token costs
CHAT_COST = 1
PDF_COST  = 10


def get_razorpay_client():
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise ValueError("Razorpay keys not configured in .env")
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


# ─── Register ─────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    data  = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    name  = data.get("name",  "").strip()
    pwd   = data.get("password", "")

    if not email or not name or not pwd:
        return jsonify({"error": "email, name and password are required."}), 400

    if len(pwd) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 409

    hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
    user   = User(email=email, name=name, password_hash=hashed, tokens=FREE_TOKENS)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({
        "message": f"Welcome to NyayaFlow, {name}! You have {FREE_TOKENS} free tokens.",
        "access_token": token,
        "user": user.to_dict(),
    }), 201


# ─── Login ────────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data  = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    pwd   = data.get("password", "")

    if not email or not pwd:
        return jsonify({"error": "email and password are required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.checkpw(pwd.encode(), user.password_hash.encode()):
        return jsonify({"error": "Invalid email or password."}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({
        "access_token": token,
        "user": user.to_dict(),
    })


# ─── Me ───────────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/me", methods=["GET"])
@jwt_required()
def me():
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify({"error": "User not found."}), 404
    return jsonify({"user": user.to_dict()})


# ─── Token balance ────────────────────────────────────────────────────────────

@auth_bp.route("/api/tokens/balance", methods=["GET"])
@jwt_required()
def token_balance():
    user = User.query.get(int(get_jwt_identity()))
    return jsonify({
        "tokens":    user.tokens,
        "chat_cost": CHAT_COST,
        "pdf_cost":  PDF_COST,
    })


# ─── Token plans ─────────────────────────────────────────────────────────────

@auth_bp.route("/api/tokens/plans", methods=["GET"])
def token_plans():
    return jsonify({
        "plans":     TOKEN_PLANS,
        "key_id":    RAZORPAY_KEY_ID,
        "chat_cost": CHAT_COST,
        "pdf_cost":  PDF_COST,
    })


# ─── Create Razorpay order ────────────────────────────────────────────────────

@auth_bp.route("/api/tokens/order", methods=["POST"])
@jwt_required()
def create_order():
    data    = request.get_json(silent=True) or {}
    plan_id = data.get("plan_id", "")

    plan = next((p for p in TOKEN_PLANS if p["id"] == plan_id), None)
    if not plan:
        return jsonify({"error": f"Invalid plan '{plan_id}'."}), 400

    user = User.query.get(int(get_jwt_identity()))

    try:
        client = get_razorpay_client()
        order  = client.order.create({
            "amount":   plan["price_paise"],
            "currency": "INR",
            "notes": {
                "user_id":         str(user.id),
                "tokens_to_credit": str(plan["tokens"]),
                "plan_id":          plan_id,
            }
        })

        # Save pending transaction
        txn = Transaction(
            user_id           = user.id,
            razorpay_order_id = order["id"],
            amount_paise      = plan["price_paise"],
            tokens_purchased  = plan["tokens"],
            status            = "created",
        )
        db.session.add(txn)
        db.session.commit()

        return jsonify({
            "order_id":    order["id"],
            "amount":      plan["price_paise"],
            "currency":    "INR",
            "key_id":      RAZORPAY_KEY_ID,
            "plan":        plan,
            "user_name":   user.name,
            "user_email":  user.email,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Verify Razorpay payment ─────────────────────────────────────────────────

@auth_bp.route("/api/tokens/verify", methods=["POST"])
@jwt_required()
def verify_payment():
    """
    Razorpay sends back after payment:
      razorpay_order_id, razorpay_payment_id, razorpay_signature
    We verify the signature using HMAC SHA256 and credit tokens.
    """
    data = request.get_json(silent=True) or {}
    order_id   = data.get("razorpay_order_id", "")
    payment_id = data.get("razorpay_payment_id", "")
    signature  = data.get("razorpay_signature", "")

    if not order_id or not payment_id or not signature:
        return jsonify({"error": "Missing payment details."}), 400

    # Verify signature
    msg      = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return jsonify({"error": "Payment verification failed. Invalid signature."}), 400

    # Find transaction
    txn = Transaction.query.filter_by(razorpay_order_id=order_id).first()
    if not txn:
        return jsonify({"error": "Transaction not found."}), 404

    if txn.status == "paid":
        return jsonify({"error": "Payment already processed."}), 409

    user = User.query.get(int(get_jwt_identity()))
    if not user or txn.user_id != user.id:
        return jsonify({"error": "Unauthorized."}), 403

    # Credit tokens
    txn.razorpay_payment_id = payment_id
    txn.status              = "paid"
    user.tokens            += txn.tokens_purchased
    db.session.commit()

    return jsonify({
        "message":          f"Payment successful! {txn.tokens_purchased} tokens added.",
        "tokens_purchased": txn.tokens_purchased,
        "new_balance":      user.tokens,
    })


# ─── Chat history ─────────────────────────────────────────────────────────────

@auth_bp.route("/api/history", methods=["GET"])
@jwt_required()
def chat_history():
    user  = User.query.get(int(get_jwt_identity()))
    limit = min(int(request.args.get("limit", 50)), 100)

    messages = (
        ChatMessage.query
        .filter_by(user_id=user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify({
        "messages": [m.to_dict() for m in reversed(messages)],
        "total":    ChatMessage.query.filter_by(user_id=user.id).count(),
    })