"""Utility helpers for YouTube URL handling and prompt preparation."""

import re
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import ValidationError


def parse_url(url):
    """Parse a URL string and return the parsed result."""
    return urlparse(url)


def get_url_host(parsed_url):
    """Return the normalized host of a parsed URL."""
    return parsed_url.netloc.lower()


def get_short_video_id(parsed_url):
    """Return the video ID from a youtu.be URL."""
    return parsed_url.path.strip('/')


def get_watch_video_id(parsed_url):
    """Return the video ID from a standard watch URL."""
    return parse_qs(parsed_url.query).get('v', [None])[0]


def get_path_parts(parsed_url):
    """Split a URL path into clean path parts."""
    return parsed_url.path.strip('/').split('/')


def get_second_path_part(parsed_url):
    """Return the second part of a split URL path if available."""
    parts = get_path_parts(parsed_url)
    if len(parts) >= 2 and parts[1]:
        return parts[1]
    return None


def extract_video_id_from_short_url(parsed_url):
    """Extract the video ID from a short YouTube URL."""
    if get_url_host(parsed_url) not in ['youtu.be', 'www.youtu.be']:
        return None
    return get_short_video_id(parsed_url) or None


def extract_video_id_from_watch_url(parsed_url):
    """Extract the video ID from a standard YouTube watch URL."""
    valid_hosts = ['youtube.com', 'www.youtube.com', 'm.youtube.com']
    if get_url_host(parsed_url) not in valid_hosts:
        return None
    if parsed_url.path != '/watch':
        return None
    return get_watch_video_id(parsed_url)


def extract_video_id_from_shorts_url(parsed_url):
    """Extract the video ID from a YouTube shorts URL."""
    valid_hosts = ['youtube.com', 'www.youtube.com', 'm.youtube.com']
    if get_url_host(parsed_url) not in valid_hosts:
        return None
    if not parsed_url.path.startswith('/shorts/'):
        return None
    return get_second_path_part(parsed_url)


def extract_video_id_from_embed_url(parsed_url):
    """Extract the video ID from a YouTube embed URL."""
    valid_hosts = ['youtube.com', 'www.youtube.com', 'm.youtube.com']
    if get_url_host(parsed_url) not in valid_hosts:
        return None
    if not parsed_url.path.startswith('/embed/'):
        return None
    return get_second_path_part(parsed_url)


def raise_invalid_youtube_url():
    """Raise a validation error for invalid YouTube URLs."""
    raise ValidationError({'url': 'Invalid YouTube URL.'})


def extract_youtube_video_id(url):
    """Extract a YouTube video ID from supported YouTube URL formats."""
    parsed_url = parse_url(url)
    video_id = extract_video_id_from_short_url(parsed_url)
    video_id = video_id or extract_video_id_from_watch_url(parsed_url)
    video_id = video_id or extract_video_id_from_shorts_url(parsed_url)
    video_id = video_id or extract_video_id_from_embed_url(parsed_url)
    if not video_id:
        raise_invalid_youtube_url()
    return video_id


def build_canonical_youtube_url(video_id):
    """Build the canonical YouTube watch URL from a video ID."""
    return f'https://www.youtube.com/watch?v={video_id}'


def remove_json_fence_start(value):
    """Remove a leading markdown json code fence."""
    return re.sub(r'^```json\s*', '', value, flags=re.IGNORECASE)


def remove_code_fence_start(value):
    """Remove a leading generic markdown code fence."""
    return re.sub(r'^```\s*', '', value)


def remove_code_fence_end(value):
    """Remove a trailing markdown code fence."""
    return re.sub(r'\s*```$', '', value)


def strip_markdown_code_fences(value):
    """Remove markdown code fences from a text value."""
    cleaned_value = value.strip()
    cleaned_value = remove_json_fence_start(cleaned_value)
    cleaned_value = remove_code_fence_start(cleaned_value)
    cleaned_value = remove_code_fence_end(cleaned_value)
    return cleaned_value.strip()


def build_quiz_prompt(transcript):
    """Build the Gemini prompt for quiz generation from a transcript."""
    return f"""
Based on the following transcript, generate a quiz in valid JSON format.

The quiz must follow this exact structure:

{{
    "title": "Create a concise quiz title based on the topic of the transcript.",
    "description": "Summarize the transcript in maximum 150 characters. The description must never exceed 150 characters and must not include any quiz questions or answers.",
    "questions": [
    {{
        "question_title": "The question goes here.",
        "question_options": ["Option A", "Option B", "Option C", "Option D"],
        "answer": "The correct answer from the above options"
    }}
    ]
}}

Requirements:
- Create exactly 10 questions.
- Each question must have exactly 4 distinct answer options.
- Only one correct answer is allowed per question, and it must be present in "question_options".
- The output must be valid JSON and parsable as-is.
- Do not include explanations, comments, markdown, or any text outside the JSON.
- The "description" field must never be longer than 150 characters.

Transcript:
{transcript}
""".strip()