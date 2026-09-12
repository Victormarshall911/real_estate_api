"""
Serializers for Crime & Offense Reporting.
"""
from rest_framework import serializers
from .models import CrimeReport


class CrimeReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrimeReport
        fields = [
            'id', 'category', 'title', 'description',
            'suspect_name', 'suspect_phone', 'suspect_bank_account',
            'property_listing', 'reported_user', 'financial_loss',
            'incident_date', 'incident_location', 'evidence_file', 'evidence_file_2'
        ]
        read_only_fields = ['id']

    def validate_title(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Please provide a meaningful title summary (at least 5 characters).")
        return value.strip()

    def validate_description(self, value):
        if len(value.strip()) < 20:
            raise serializers.ValidationError("Please provide sufficient details of what occurred (at least 20 characters).")
        return value.strip()


class CrimeReportListSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    property_title = serializers.CharField(source='property_listing.title', read_only=True, default=None)

    class Meta:
        model = CrimeReport
        fields = [
            'id', 'category', 'category_display', 'title', 'status',
            'status_display', 'financial_loss', 'property_title',
            'incident_date', 'created_at', 'resolved_at'
        ]
        read_only_fields = fields


class CrimeReportDetailSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    property_title = serializers.CharField(source='property_listing.title', read_only=True, default=None)
    evidence_file_url = serializers.SerializerMethodField()
    evidence_file_2_url = serializers.SerializerMethodField()
    reporter_email = serializers.EmailField(source='reporter.email', read_only=True)
    reporter_name = serializers.CharField(source='reporter.full_name', read_only=True)

    class Meta:
        model = CrimeReport
        fields = [
            'id', 'category', 'category_display', 'title', 'description',
            'suspect_name', 'suspect_phone', 'suspect_bank_account',
            'property_listing', 'property_title', 'reported_user',
            'financial_loss', 'incident_date', 'incident_location',
            'evidence_file_url', 'evidence_file_2_url',
            'status', 'status_display', 'police_report_reference',
            'resolution_summary', 'reporter_email', 'reporter_name',
            'created_at', 'updated_at', 'resolved_at'
        ]
        read_only_fields = fields

    def get_evidence_file_url(self, obj):
        if obj.evidence_file:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.evidence_file.url) if request else obj.evidence_file.url
        return None

    def get_evidence_file_2_url(self, obj):
        if obj.evidence_file_2:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.evidence_file_2.url) if request else obj.evidence_file_2.url
        return None
