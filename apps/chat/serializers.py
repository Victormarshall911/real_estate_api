"""
Serializers for chat sessions and messages.
"""
from rest_framework import serializers
from .models import ChatSession, ChatMessage
from accounts.serializers import CustomUserSerializer
from agents.serializers import AgentProfileSerializer


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ['id', 'session', 'sender', 'sender_name', 'text', 'is_read', 'created_at', 'is_mine']
        read_only_fields = ['id', 'session', 'sender', 'sender_name', 'is_read', 'created_at', 'is_mine']

    def get_is_mine(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return obj.sender == request.user
        return False


class ChatSessionSerializer(serializers.ModelSerializer):
    client = CustomUserSerializer(source='connection.user', read_only=True)
    agent = AgentProfileSerializer(source='connection.agent', read_only=True)
    connection_status = serializers.CharField(source='connection.status', read_only=True)
    connection_buyer_completed = serializers.BooleanField(source='connection.buyer_completed', read_only=True)
    connection_agent_completed = serializers.BooleanField(source='connection.agent_completed', read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            'id', 'connection', 'client', 'agent', 'connection_status', 
            'connection_buyer_completed', 'connection_agent_completed',
            'created_at', 'updated_at', 'is_active', 'last_message', 'unread_count'
        ]

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return ChatMessageSerializer(last_msg, context=self.context).data
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
        return 0
