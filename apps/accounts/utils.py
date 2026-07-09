from django.conf import settings

def get_clean_media_url(file_or_url, request=None):
    """
    Normalizes local relative paths, Cloudinary protocol-relative URLs,
    and absolute URLs to prevent broken image references.
    Supports both Django FileField/ImageField and raw URL strings.
    """
    if not file_or_url:
        return None
    
    url = file_or_url if isinstance(file_or_url, str) else getattr(file_or_url, 'url', None)
    if not url:
        return None

    if url.startswith('//'):
        return f"https:{url}"
    if url.startswith('http://') or url.startswith('https://') or url.startswith('data:'):
        return url
    if not url.startswith('/'):
        if url.startswith('media/'):
            url = f"/{url}"
        else:
            url = f"/media/{url}"

    if request:
        return request.build_absolute_uri(url)
    
    if getattr(settings, 'DEBUG', True):
        return f"http://localhost:8001{url}"
    return f"https://real-estate-api-orbx.onrender.com{url}"
