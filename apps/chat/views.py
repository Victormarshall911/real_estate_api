"""
REST API Views for Chat (historical data and session listing).
Real-time messaging is handled by WebSockets (consumers.py).
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from .models import ChatSession, ChatMessage
from .serializers import ChatSessionSerializer, ChatMessageSerializer


class ChatSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve chat sessions for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatSessionSerializer

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', '') == 'agent' and hasattr(user, 'agent_profile'):
            return ChatSession.objects.filter(
                Q(connection__user=user) | Q(connection__agent=user.agent_profile)
            )
        return ChatSession.objects.filter(connection__user=user)

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
