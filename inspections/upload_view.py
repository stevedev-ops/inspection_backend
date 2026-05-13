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
    ext = file_obj.name.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    path = default_storage.save(filename, file_obj)
    url = default_storage.url(path)
    
    return Response({'publicUrl': url})
