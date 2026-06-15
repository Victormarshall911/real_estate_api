"""
Models for the Real-Time Chat app.
"""
import uuid
from django.db import models
from django.conf import settings

from agents.models import AgentConnection


class ChatSession(models.Model):
    """
    A chat session between a client (user) and an agent.
    Tied to an AgentConnection.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.OneToOneField(
        AgentConnection,
        on_delete=models.CASCADE,
        related_name='chat_session'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-updated_at']

    def __str__(self):
        return f"Chat for Connection {self.connection.id}"

    @property
    def participants(self):
        return [self.connection.client, self.connection.agent.user]


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
