"""Prompt templates and configuration constants."""

from __future__ import annotations

TEMPLATES = {
    "linkedin": {
        "professional": (
            "Rewrite the following text as a professional LinkedIn post of about 100–120 words. "
            "Use a formal, business-oriented tone suitable for industry professionals. "
            "Keep language precise, objective, and informative. Avoid emojis or slang. "
            "Emphasize key insights and end with a reflective question or thought-provoking statement.\n\n"
            "Content:\n{content}"
        ),
        "casual": (
            "Rewrite the following text as a casual and engaging LinkedIn post (100–120 words). "
            "Use friendly, conversational language with occasional emojis and rhetorical questions. "
            "Make it sound like a personal insight shared by a professional, not a corporate statement.\n\n"
            "Content:\n{content}"
        ),
        "promotional": (
            "Rewrite the following text as a promotional LinkedIn post (100–120 words). "
            "Use energetic, persuasive language focused on benefits and innovation. "
            "Encourage readers to take action or reflect on future opportunities. "
            "Add 3–5 relevant professional hashtags at the end.\n\n"
            "Content:\n{content}"
        )
    },

    "instagram": {
        "professional": (
            "Create two short Instagram captions (under 80 words each) from the following content in a professional tone. "
            "Keep them polished but engaging. Avoid slang, keep one emoji if relevant, and include 3–5 professional hashtags.\n\n"
            "Content:\n{content}"
        ),
        "casual": (
            "Create two Instagram captions (under 80 words each) using a casual, relatable tone. "
            "Use emojis, fun expressions, and hashtags that connect with the audience. "
            "Make it sound like a friendly, upbeat post from a creative marketer.\n\n"
            "Content:\n{content}"
        ),
        "promotional": (
            "Write two catchy Instagram captions promoting this topic. "
            "Use exciting language, emojis, and 4–6 marketing hashtags. "
            "Focus on calls-to-action or benefits while keeping captions short and shareable.\n\n"
            "Content:\n{content}"
        )
    },

    "youtube": {
        "professional": (
            "Write a 30-second YouTube Shorts script summarizing the following content in a professional tone. "
            "Use a confident, clear, and informative delivery style suitable for business or educational audiences. "
            "Avoid slang or excessive emotion.\n\n"
            "Content:\n{content}"
        ),
        "casual": (
            "Write a 30-second YouTube Shorts script using a casual, energetic tone. "
            "Start with a catchy hook question or fun statement. "
            "Use conversational words and light humor to keep it engaging.\n\n"
            "Content:\n{content}"
        ),
        "promotional": (
            "Write a short, high-energy YouTube Shorts script (around 30 seconds) promoting this topic. "
            "Use persuasive, motivational language with a clear call-to-action at the end. "
            "Start with a powerful hook to grab attention.\n\n"
            "Content:\n{content}"
        )
    }
}


TONES = {
    "Professional": "professional",
    "Casual": "casual",
    "Promotional": "promotional",
}


PLATFORMS = {
    "LinkedIn": "linkedin",
    "Instagram": "instagram",
    "YouTube": "youtube",
}


__all__ = ["TEMPLATES", "TONES", "PLATFORMS"]

