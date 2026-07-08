"""
Models for the Real-Time Chat app.
"""
import uuid
from django.db import models
from django.conf import settings

from agents.models import AgentConnection


class ChatSession(models.Model):
    """
    A chat session between a client (user) and an agent or realtor.
    Tied to an optional AgentConnection.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.OneToOneField(
        AgentConnection,
        on_delete=models.CASCADE,
        related_name='chat_session',
        null=True,
        blank=True
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='buyer_chat_sessions',
        null=True,
        blank=True
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seller_chat_sessions',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-updated_at']

    def __str__(self):
        if self.connection:
            return f"Chat for Connection {self.connection.id}"
        buyer_name = self.buyer.full_name if self.buyer else "Unknown"
        seller_name = self.seller.full_name if self.seller else "Unknown"
        return f"Direct Chat: {buyer_name} <-> {seller_name}"

    @property
    def participants(self):
        buyer_user = self.buyer or (self.connection.user if self.connection else None)
        seller_user = self.seller or (self.connection.agent.user if self.connection else None)
        return [u for u in [buyer_user, seller_user] if u is not None]


class ChatMessage(models.Model):
    """
    Individual message in a chat session.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"Message by {self.sender.full_name} at {self.created_at}"
