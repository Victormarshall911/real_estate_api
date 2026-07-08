"""
REST API Views for Chat (historical data and session listing).
Real-time messaging is handled by WebSockets (consumers.py).
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.contrib.auth import get_user_model

from .models import ChatSession, ChatMessage
from .serializers import ChatSessionSerializer, ChatMessageSerializer

User = get_user_model()


class ChatSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve chat sessions for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatSessionSerializer

    def get_queryset(self):
        user = self.request.user
        # Retrieve all sessions where the user is either the buyer or the seller
        return ChatSession.objects.filter(Q(buyer=user) | Q(seller=user))

    @action(detail=False, methods=['post'])
    def start_direct(self, request):
        """Start a direct chat with a Realtor, Agent, or another user."""
        seller_id = request.data.get('seller_id')
        if not seller_id:
            return Response({"error": "seller_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            seller = User.objects.get(id=seller_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
            
        if seller == request.user:
            return Response({"error": "You cannot chat with yourself."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Get or create a session where the user and seller are participants and it's a direct chat (connection is null)
        session = ChatSession.objects.filter(
            Q(buyer=request.user, seller=seller) | Q(buyer=seller, seller=request.user),
            connection__isnull=True
        ).first()
        
        created = False
        if not session:
            session = ChatSession.objects.create(
                buyer=request.user,
                seller=seller,
                connection=None
            )
            created = True
            
        serializer = self.get_serializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get message history for a session."""
        session = self.get_object()
        messages = session.messages.all()
        
        # Mark unread messages as read
        unread = messages.filter(is_read=False).exclude(sender=request.user)
        unread.update(is_read=True)

        serializer = ChatMessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Fallback REST endpoint for sending a message if WebSocket fails."""
        session = self.get_object()
        text = request.data.get('text')
        
        if not text:
            return Response({"error": "Message text is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        message = ChatMessage.objects.create(
            session=session,
            sender=request.user,
            text=text
        )
        
        # Update session timestamp
        session.save()
        
        serializer = ChatMessageSerializer(message, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
