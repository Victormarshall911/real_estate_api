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
    if url.startswith('http'):
        return url
    if request:
        return request.build_absolute_uri(url)
    return f"https://real-estate-api-orbx.onrender.com{url}"
