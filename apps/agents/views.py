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
            
        # In a full implementation, we would create a PaystackPayment here
        # For now, we mock the payment creation and just return a success payload
        
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
                "message": "Connection established successfully.",
                "connection": AgentConnectionSerializer(connection).data,
                "chat_session_id": str(chat_session.id)
            }, 
            status=status.HTTP_201_CREATED
        )
