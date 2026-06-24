"""
Views for Agents: listing profiles, adding locations, and initiating connections.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from .models import AgentProfile, AgentLocationPricing, AgentConnection
from .serializers import (
    AgentProfileSerializer, 
    AgentProfileCreateUpdateSerializer,
    AgentLocationPricingSerializer,
    AgentConnectionSerializer
)
from chat.models import ChatSession


class AgentProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows agents to be viewed or edited.
    """
    queryset = AgentProfile.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_verified']
    search_fields = ['company_name', 'company_location', 'bio', 'location_prices__location', 'location_prices__state']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AgentProfileCreateUpdateSerializer
        return AgentProfileSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Get the current user's agent profile."""
        try:
            profile = AgentProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except AgentProfile.DoesNotExist:
            return Response(
                {"error": "You do not have an agent profile."}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_location(self, request, pk=None):
        """Add pricing for a specific location to this agent."""
        agent = self.get_object()
        
        # Only the agent themselves can add locations
        if agent.user != request.user:
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = AgentLocationPricingSerializer(data=request.data)
        if serializer.is_valid():
            # Check for existing
            state = serializer.validated_data['state']
            location = serializer.validated_data['location']
            if AgentLocationPricing.objects.filter(agent=agent, state=state, location=location).exists():
                return Response(
                    {"error": "Pricing for this location already exists."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            serializer.save(agent=agent)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def remove_location(self, request, pk=None):
        """Remove a specific location pricing from this agent."""
        agent = self.get_object()
        
        # Only the agent themselves can remove locations
        if agent.user != request.user:
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
            
        location_id = request.data.get('location_id')
        if not location_id:
            return Response({"error": "location_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            location = AgentLocationPricing.objects.get(id=location_id, agent=agent)
            location.delete()
            return Response({"message": "Location removed successfully."}, status=status.HTTP_200_OK)
        except AgentLocationPricing.DoesNotExist:
            return Response({"error": "Location not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def rate(self, request, pk=None):
        """Rate an agent."""
        agent = self.get_object()
        
        # Check if user has an active/completed connection with this agent
        # For now we just allow any authenticated user to rate (simplified for mockup)
        
        rating = request.data.get('rating')
        comment = request.data.get('comment', '')
        
        if not rating or not isinstance(rating, int) or not (1 <= rating <= 5):
            return Response({"error": "Valid rating between 1 and 5 is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        from .models import AgentReview
        from .serializers import AgentReviewSerializer
        
        review, created = AgentReview.objects.update_or_create(
            agent=agent,
            user=request.user,
            defaults={'rating': rating, 'comment': comment}
        )
        
        return Response(AgentReviewSerializer(review).data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)


class AgentConnectionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View connections for the authenticated user.
    """
    serializer_class = AgentConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Return connections where the user is the client, OR where the user is the agent
        user = self.request.user
        return AgentConnection.objects.filter(models.Q(user=user) | models.Q(agent__user=user))

    @action(detail=False, methods=['post'])
    def initiate(self, request):
        """
        Initiate a connection with an agent.
        Creates a pending connection and a pending Paystack payment.
        """
        agent_id = request.data.get('agent_id')
        location_id = request.data.get('location_id')
        
        try:
            agent = AgentProfile.objects.get(id=agent_id)
            location = AgentLocationPricing.objects.get(id=location_id, agent=agent)
        except (AgentProfile.DoesNotExist, AgentLocationPricing.DoesNotExist):
            return Response({"error": "Invalid agent or location pricing."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Check if active connection exists
        existing = AgentConnection.objects.filter(user=request.user, agent=agent, status='active').first()
        if existing:
            return Response({"error": "You already have an active connection with this agent."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Check wallet balance and deduct
        from apps.wallets.models import Wallet, WalletTransaction
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        fee = location.connection_fee
        
        if wallet.balance < fee:
            return Response({"error": "Insufficient wallet balance. Please deposit funds."}, status=status.HTTP_400_BAD_REQUEST)
            
        wallet.balance -= fee
        wallet.save()
        
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='payment',
            amount=fee,
            reference=f"escrow_agent_{agent.id}_{uuid.uuid4().hex[:8]}",
            description=f"Connection fee held in escrow for {agent.user.first_name}"
        )
        
        connection = AgentConnection.objects.create(
            user=request.user,
            agent=agent,
            location_pricing=location,
            status='active'
        )
        
        # Auto-create a ChatSession so chat is immediately available
        chat_session = ChatSession.objects.create(connection=connection)
        
        agent.total_connections += 1
        agent.save(update_fields=['total_connections'])
        
        return Response(
            {
                "message": "Connection established. Funds held in escrow.",
                "connection": AgentConnectionSerializer(connection).data,
                "chat_session_id": str(chat_session.id)
            }, 
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def complete_deal(self, request, pk=None):
        """Mark connection as completed by either party."""
        connection = self.get_object()
        
        if connection.status != 'active':
            return Response({"error": "Connection is not active."}, status=status.HTTP_400_BAD_REQUEST)
            
        if request.user == connection.user:
            connection.buyer_completed = True
        elif hasattr(request.user, 'agent_profile') and request.user.agent_profile == connection.agent:
            connection.agent_completed = True
        else:
            return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
            
        if connection.buyer_completed and connection.agent_completed:
            connection.status = 'closed'
            
            # Release funds to agent's wallet
            from apps.wallets.models import Wallet, WalletTransaction
            agent_wallet, _ = Wallet.objects.get_or_create(user=connection.agent.user)
            fee = connection.location_pricing.connection_fee
            
            agent_wallet.balance += fee
            agent_wallet.save()
            
            WalletTransaction.objects.create(
                wallet=agent_wallet,
                transaction_type='receipt',
                amount=fee,
                reference=f"release_agent_{connection.id}_{uuid.uuid4().hex[:8]}",
                description=f"Escrow released for connection with {connection.user.first_name}"
            )
            
        connection.save()
        return Response({"message": "Status updated.", "status": connection.status})
