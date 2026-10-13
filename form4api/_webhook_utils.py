from __future__ import annotations

import hashlib
import hmac


def verify_webhook(payload: str | bytes, signature: str, secret: str) -> bool:
    """Return True if the X-Insider-Signature header matches the payload.

    Usage::

        body = request.get_data(as_text=True)
        sig  = request.headers["X-Insider-Signature"]
        if not verify_webhook(body, sig, WEBHOOK_SECRET):
            abort(401)
    """
    if isinstance(payload, str):
        payload = payload.encode()
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    if not isinstance(signature, str):
        return False
    # Compare as bytes: compare_digest raises TypeError on a non-ASCII str, and a
    # garbage header should be a failed check, not an exception.
    return hmac.compare_digest(expected.encode(), signature.encode())



