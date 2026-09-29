# Copyright (c) 2026, Agilasoft Technologies Inc. and contributors
# For license information, please see license.txt

"""Strip auto-assigned Gravatar URLs from Lead profile image fields."""

from __future__ import annotations

GRAVATAR_HOST_MARKERS = ("gravatar.com", "secure.gravatar.com")


def is_gravatar_url(url: str | None) -> bool:
	if not url:
		return False
	lower = str(url).strip().lower()
	return any(marker in lower for marker in GRAVATAR_HOST_MARKERS)


def clear_gravatar_image(doc, method=None):
	"""before_save: remove Gravatar auto-avatars; keep explicit /files uploads."""
	image = getattr(doc, "image", None)
	if is_gravatar_url(image):
		doc.image = ""
