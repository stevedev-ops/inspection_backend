from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import permissions, status
from rest_framework.response import Response
from django.core.files.storage import default_storage
from django.conf import settings
import uuid
import os

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_photo(request):
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    file_obj = request.FILES['file']
    
    # 1. Size Validation (5MB limit)
    MAX_SIZE = 5 * 1024 * 1024 # 5MB
    if file_obj.size > MAX_SIZE:
        return Response({'error': 'File too large. Max 5MB allowed.'}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Extension Validation
    ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'heic']
    ext = file_obj.name.split('.')[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return Response({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}, status=status.HTTP_400_BAD_REQUEST)

    # 3. MIME Type Validation
    ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/jpg']
    if file_obj.content_type not in ALLOWED_MIME_TYPES:
        return Response({'error': 'Invalid file content. Strictly images allowed.'}, status=status.HTTP_400_BAD_REQUEST)

    filename = f"{uuid.uuid4()}.{ext}"
    path = default_storage.save(filename, file_obj)
    url = default_storage.url(path)
    
    return Response({'publicUrl': url})
