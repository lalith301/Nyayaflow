"""
NyayaFlow - Flask API Server v2
Now with JWT auth, token system, chat history, and Razorpay payments.

Public endpoints:
  POST /api/auth/register
  POST /api/auth/login
  GET  /api/doc-types
  GET  /api/health

Protected endpoints (JWT required):
  POST /api/chat            → costs 1 token
  POST /api/generate-doc    → costs 10 tokens
  POST /api/transcribe      → free (voice input)
  GET  /api/auth/me
  GET  /api/tokens/balance
  GET  /api/tokens/plans
  POST /api/tokens/order
  POST /api/tokens/verify
  GET  /api/history
"""

import os
import json
import io
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ─── Config ───────────────────────────────────────────────────────────────────
app.config["SQLALCHEMY_DATABASE_URI"]        = os.getenv("DATABASE_URL", "sqlite:///nyayaflow.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"]                 = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
app.config["JWT_ACCESS_TOKEN_EXPIRES"]       = False   # tokens don't expire (simplest for demo)

# ─── Init extensions ──────────────────────────────────────────────────────────
from models import db, User, ChatMessage
db.init_app(app)

jwt = JWTManager(app)

# ─── Register auth blueprint ──────────────────────────────────────────────────
from auth import auth_bp, CHAT_COST, PDF_COST
app.register_blueprint(auth_bp)

# ─── Create tables on startup ─────────────────────────────────────────────────
with app.app_context():
    db.create_all()
    print("[nyayaflow] Database ready.")


# ─── Token deduction helper ───────────────────────────────────────────────────

def deduct_tokens(user_id: int, cost: int) -> tuple[bool, User]:
    """
    Deduct `cost` tokens from user. Returns (success, user).
    Returns False if insufficient tokens.
    """
    user = User.query.get(user_id)
    if not user:
        return False, None
    if user.tokens < cost:
        return False, user
    user.tokens -= cost
    db.session.commit()
    return True, user


# ─── Health ───────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "NyayaFlow API", "version": "2.0.0"})


# ─── Doc types (public) ───────────────────────────────────────────────────────

@app.route("/api/doc-types", methods=["GET"])
def doc_types():
    from document_gen import SUPPORTED_DOC_TYPES
    return jsonify({"doc_types": SUPPORTED_DOC_TYPES})


# ─── /api/chat ────────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
@jwt_required()
def chat():
    user_id = int(get_jwt_identity())
    data    = request.get_json(silent=True) or {}
    query   = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Field 'query' is required."}), 400

    # Check + deduct tokens
    ok, user = deduct_tokens(user_id, CHAT_COST)
    if not ok:
        return jsonify({
            "error":         "Insufficient tokens. Please purchase more tokens to continue.",
            "tokens_needed": CHAT_COST,
            "tokens_have":   user.tokens if user else 0,
        }), 402

    try:
        from agent import get_agent_answer
        result = get_agent_answer(query)

        # Save to chat history
        user_msg = ChatMessage(
            user_id     = user_id,
            role        = "user",
            content     = query,
            tokens_used = CHAT_COST,
        )
        ai_msg = ChatMessage(
            user_id     = user_id,
            role        = "assistant",
            content     = result["answer"],
            sources     = json.dumps(result.get("sources", [])),
            used_agent  = result.get("used_agent", False),
            law_fetched = result.get("law_fetched"),
            tokens_used = 0,
        )
        db.session.add_all([user_msg, ai_msg])
        db.session.commit()

        result["tokens_remaining"] = user.tokens
        return jsonify(result)

    except Exception as e:
        # Refund token on error
        user.tokens += CHAT_COST
        db.session.commit()
        print(f"[chat] Error: {e}")
        return jsonify({"error": "Internal server error. Token refunded."}), 500


# ─── /api/generate-doc ────────────────────────────────────────────────────────

@app.route("/api/generate-doc", methods=["POST"])
@jwt_required()
def generate_doc():
    user_id  = int(get_jwt_identity())
    data     = request.get_json(silent=True) or {}
    doc_type = data.get("doc_type", "").strip()
    fields   = data.get("fields", {})

    if not doc_type:
        return jsonify({"error": "Field 'doc_type' is required."}), 400
    if not isinstance(fields, dict) or not fields:
        return jsonify({"error": "Field 'fields' must be a non-empty object."}), 400

    # Check + deduct tokens
    ok, user = deduct_tokens(user_id, PDF_COST)
    if not ok:
        return jsonify({
            "error":         f"Insufficient tokens. PDF generation costs {PDF_COST} tokens.",
            "tokens_needed": PDF_COST,
            "tokens_have":   user.tokens if user else 0,
        }), 402

    try:
        from document_gen import generate_legal_document, SUPPORTED_DOC_TYPES

        if doc_type not in SUPPORTED_DOC_TYPES:
            user.tokens += PDF_COST
            db.session.commit()
            return jsonify({
                "error":     f"Unknown doc_type '{doc_type}'.",
                "supported": list(SUPPORTED_DOC_TYPES.keys()),
            }), 400

        pdf_bytes = generate_legal_document(doc_type, fields)
        doc_title = SUPPORTED_DOC_TYPES[doc_type].replace(" ", "_")

        # Add identifying name to filename based on doc type
        name_field_map = {
            "rental_agreement":   fields.get("landlord_name", ""),
            "nda":                fields.get("disclosing_party", ""),
            "freelance_contract": fields.get("client_name", ""),
            "employment_offer":   fields.get("candidate_name", ""),
            "affidavit":          fields.get("deponent_name", ""),
        }
        identifier = name_field_map.get(doc_type, "")
        if identifier:
            import re
            safe_name = re.sub(r"[^\w\s-]", "", identifier).strip().replace(" ", "_")[:20]
            filename  = f"NyayaFlow_{doc_title}_{safe_name}.pdf"
        else:
            filename  = f"NyayaFlow_{doc_title}.pdf"

        from flask import make_response
        response = make_response(send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        ))
        response.headers["X-Tokens-Remaining"] = str(user.tokens)
        return response

    except ValueError as e:
        user.tokens += PDF_COST
        db.session.commit()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        user.tokens += PDF_COST
        db.session.commit()
        print(f"[generate-doc] Error: {e}")
        return jsonify({"error": "Document generation failed. Token refunded."}), 500


# ─── /api/transcribe (free) ───────────────────────────────────────────────────

@app.route("/api/transcribe", methods=["POST"])
@jwt_required()
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "Audio file required."}), 400

    audio_file  = request.files["audio"]
    ext         = os.path.splitext(audio_file.filename or "audio.wav")[1].lower() or ".wav"
    audio_bytes = audio_file.read()

    if len(audio_bytes) > 25 * 1024 * 1024:
        return jsonify({"error": "Audio file too large. Maximum 25 MB."}), 413

    try:
        from whisper_utils import transcribe_audio_bytes
        result = transcribe_audio_bytes(audio_bytes, ext=ext)
        if "error" in result:
            return jsonify(result), 400
        return jsonify({"text": result["text"], "language": result["language"]})
    except Exception as e:
        print(f"[transcribe] Error: {e}")
        return jsonify({"error": "Transcription failed."}), 500


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port  = int(os.getenv("FLASK_PORT", 8000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    print(f"[nyayaflow] Starting server on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)