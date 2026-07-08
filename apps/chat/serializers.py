"""
Serializers for chat sessions and messages.
"""
from rest_framework import serializers
from .models import ChatSession, ChatMessage
from accounts.serializers import UserSerializer
from agents.serializers import AgentProfileSerializer
from realtors.serializers import RealtorProfileSerializer
from architects.serializers import ArchitectProfileSerializer


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
    client = UserSerializer(source='buyer', read_only=True)
    agent = serializers.SerializerMethodField()
    connection_status = serializers.SerializerMethodField()
    connection_buyer_completed = serializers.SerializerMethodField()
    connection_agent_completed = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            'id', 'connection', 'client', 'agent', 'connection_status', 
            'connection_buyer_completed', 'connection_agent_completed',
            'created_at', 'updated_at', 'is_active', 'last_message', 'unread_count'
        ]

    def get_agent(self, obj):
        if obj.connection:
            return AgentProfileSerializer(obj.connection.agent, context=self.context).data
        seller = obj.seller
        if seller:
            if hasattr(seller, 'realtor_profile'):
                return RealtorProfileSerializer(seller.realtor_profile, context=self.context).data
            if hasattr(seller, 'agent_profile'):
                return AgentProfileSerializer(seller.agent_profile, context=self.context).data
            if hasattr(seller, 'architect_profile'):
                return ArchitectProfileSerializer(seller.architect_profile, context=self.context).data
            return {
                'id': None,
                'user': UserSerializer(seller, context=self.context).data,
                'company_name': 'Independent',
                'phone_number': '',
                'is_verified': False
            }
        return None

    def get_connection_status(self, obj):
        if obj.connection:
            return obj.connection.status
        return 'active'

    def get_connection_buyer_completed(self, obj):
        if obj.connection:
            return obj.connection.buyer_completed
        return False

    def get_connection_agent_completed(self, obj):
        if obj.connection:
            return obj.connection.agent_completed
        return False

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
