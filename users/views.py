from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from users.models import User
from users.serializers import UserSerializer, RegisterSerializer
from django.shortcuts import get_object_or_404


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['role', 'subcounty', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return User.objects.all()
        if user.role == 'admin':
            from django.db.models import Q
            return User.objects.filter(Q(created_by=user) | Q(id=user.id))
        return User.objects.filter(id=user.id)

    def perform_update(self, serializer):
        # Prevent self-suspension or self-activation
        if 'status' in self.request.data and serializer.instance == self.request.user:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'status': 'You cannot suspend or activate your own account. This must be done by another administrator.'})
        serializer.save()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


from inspections.utils import log_activity

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_create_user(request):
    """Replaces the Supabase RPC `admin_create_user`"""
    if request.user.role not in ['super_admin', 'admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    serializer = RegisterSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.save()
        log_activity(request.user, 'STAFF_REGISTERED', {
            'target_user': str(user.id),
            'target_email': user.email,
            'role': user.role
        })
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_purge_user(request):
    """Delete a user account. Super Admin only."""
    if request.user.role not in ['super_admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    user_id = request.data.get('user_id')
    user = get_object_or_404(User, id=user_id)
    target_info = {'id': str(user.id), 'email': user.email, 'role': user.role}
    user.delete()
    log_activity(request.user, 'STAFF_PURGED', target_info)
    return Response({'message': 'User purged successfully'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def transfer_subcounty(request):
    """Transfer a PHO or NCCG inspector to a different subcounty."""
    if request.user.role not in ['super_admin', 'admin']:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    user_id = request.data.get('user_id')
    new_subcounty = request.data.get('subcounty')

    if not user_id or not new_subcounty:
        return Response({'error': 'user_id and subcounty are required'}, status=status.HTTP_400_BAD_REQUEST)

    target = get_object_or_404(User, id=user_id)
    if target.role not in ['pho', 'nccg_inspector']:
        return Response({'error': 'Only PHO and NCCG inspectors can be transferred'}, status=status.HTTP_400_BAD_REQUEST)

    # Admin can only transfer their own staff
    if request.user.role == 'admin' and target.created_by != request.user:
        return Response({'error': 'You can only transfer your own staff'}, status=status.HTTP_403_FORBIDDEN)

    old_subcounty = target.subcounty
    target.subcounty = new_subcounty
    target.save(update_fields=['subcounty'])

    log_activity(request.user, 'STAFF_TRANSFERRED', {
        'target_user': str(target.id),
        'old_subcounty': old_subcounty,
        'new_subcounty': new_subcounty
    })

    return Response({
        'message': f'{target.full_name or target.email} transferred from {old_subcounty} to {new_subcounty}',
        'user_id': str(target.id),
        'subcounty': new_subcounty,
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def resolve_staff_login_email(request):
    """Replaces the Supabase RPC `resolve_staff_login_email`"""
    identifier = request.data.get('email')
    from django.db.models import Q
    user = User.objects.filter(Q(email=identifier) | Q(department=identifier)).first()
    if user:
        return Response({'email': user.email})
    return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
