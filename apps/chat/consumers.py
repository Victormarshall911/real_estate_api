import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

from .models import ChatSession, ChatMessage

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'chat_{self.session_id}'

        # Auth is handled via token in query string since standard headers aren't sent by JS WS
        user = await self.get_user_from_query_string()
        if isinstance(user, AnonymousUser):
            await self.close(code=4001)
            return

        self.user = user

        # Verify user has access to this session
        has_access = await self.verify_session_access(self.session_id, self.user)
        if not has_access:
            await self.close(code=4003)
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_text = text_data_json.get('message', '')

        if not message_text.strip():
            return

        # Save to DB
        msg_obj = await self.save_message(self.session_id, self.user, message_text)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': str(msg_obj.id),
                'message': message_text,
                'sender_id': str(self.user.id),
                'sender_name': self.user.full_name,
                'created_at': msg_obj.created_at.isoformat()
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'id': event['id'],
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'created_at': event['created_at']
        }))

    @database_sync_to_async
    def get_user_from_query_string(self):
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        params = dict(x.split('=') for x in query_string.split('&') if '=' in x)
        token = params.get('token')
        
        if not token:
            return AnonymousUser()
            
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            return User.objects.get(id=user_id)
        except Exception:
            return AnonymousUser()

    @database_sync_to_async
    def verify_session_access(self, session_id, user):
        try:
            session = ChatSession.objects.select_related('connection__user', 'connection__agent__user').get(id=session_id)
            if session.connection.user == user or session.connection.agent.user == user:
                return True
            return False
        except ChatSession.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, session_id, user, text):
        session = ChatSession.objects.get(id=session_id)
        msg = ChatMessage.objects.create(
            session=session,
            sender=user,
            text=text
        )
        session.save() # update updated_at
        return msg
