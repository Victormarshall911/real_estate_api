"""
Views for handling subscription plans and user subscriptions.
"""
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import SubscriptionPlan, UserSubscription
from .serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List available subscription plans.
    """
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]


class UserSubscriptionViewSet(viewsets.ViewSet):
    """
    Manage the authenticated user's subscription.
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get the user's current subscription."""
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            serializer = UserSubscriptionSerializer(subscription)
            return Response(serializer.data)
        except UserSubscription.DoesNotExist:
            return Response(
                {"error": "You do not have an active subscription."}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def subscribe(self, request):
        """
        Subscribe to a plan.
        Creates a pending Paystack payment (mocked for now).
        """
        plan_id = request.data.get('plan_id')
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Invalid plan."}, status=status.HTTP_400_BAD_REQUEST)

        # Mocking successful subscription creation/update
        subscription, created = UserSubscription.objects.update_or_create(
            user=request.user,
            defaults={
                'plan': plan,
                'status': UserSubscription.Status.ACTIVE,
                'current_period_start': timezone.now(),
                'cancel_at_period_end': False,
            }
        )
        # Note: current_period_end is handled in model save() if not set

        return Response(
            {
                "message": f"Successfully subscribed to {plan.name}.",
                "subscription": UserSubscriptionSerializer(subscription).data
            },
            status=status.HTTP_200_OK
        )
