"""
AI-assisted natural language property discovery endpoint.
"""
import re
from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PropertyListing
from .serializers import PropertyListSerializer


class AIAssistantSearchView(APIView):
    """
    POST /api/v1/properties/ai-search/
    Parses natural language budget, state/location, and property type to return recommended matches.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        query = request.data.get('query', '').strip()
        if not query:
            return Response({'error': 'Query is required'}, status=status.HTTP_400_BAD_REQUEST)

        q_lower = query.lower()
        queryset = PropertyListing.objects.filter(status=PropertyListing.Status.AVAILABLE)

        # 1. Parse budget in millions
        million_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:m|million|milli)', q_lower)
        if million_match:
            budget = float(million_match.group(1)) * 1_000_000
            queryset = queryset.filter(price__lte=budget)

        # 2. Location filter matches
        for loc in ['lagos', 'abuja', 'delta', 'rivers', 'oyo', 'enugu', 'asaba', 'lekki', 'epe', 'maitama', 'ikoyi']:
            if loc in q_lower:
                queryset = queryset.filter(
                    Q(state__icontains=loc) |
                    Q(location__icontains=loc) |
                    Q(title__icontains=loc)
                )

        # 3. Document keywords
        if 'c of o' in q_lower or 'co of o' in q_lower:
            queryset = queryset.filter(has_c_of_o=True)
        if 'survey' in q_lower:
            queryset = queryset.filter(has_survey_plan=True)

        results = queryset.order_by('-is_title_verified', '-created_at')[:4]
        serialized = PropertyListSerializer(results, many=True, context={'request': request}).data

        return Response({
            'query': query,
            'match_count': len(serialized),
            'results': serialized,
            'summary': f"Found {len(serialized)} matching verified properties."
        }, status=status.HTTP_200_OK)
