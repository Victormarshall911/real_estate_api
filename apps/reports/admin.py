from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import CrimeReport


@admin.register(CrimeReport)
class CrimeReportAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'category', 'status', 'reporter',
        'financial_loss', 'suspect_name', 'has_evidence', 'created_at'
    )
    list_filter = ('status', 'category', 'created_at', 'incident_date')
    search_fields = (
        'title', 'description', 'suspect_name', 'suspect_phone',
        'suspect_bank_account', 'reporter__email', 'police_report_reference'
    )
    readonly_fields = ('id', 'created_at', 'updated_at', 'evidence_preview')
    actions = [
        'mark_under_investigation',
        'escalate_to_authorities',
        'mark_action_taken',
        'mark_resolved',
        'dismiss_report'
    ]

    def has_evidence(self, obj):
        return bool(obj.evidence_file or obj.evidence_file_2)
    has_evidence.boolean = True
    has_evidence.short_description = 'Evidence Uploaded'

    def evidence_preview(self, obj):
        links = []
        if obj.evidence_file:
            links.append(format_html('<a href="{}" target="_blank" style="padding: 6px 12px; background: #2563eb; color: #fff; border-radius: 6px; text-decoration: none; font-weight: bold; margin-right: 8px;">View Primary Evidence ↗</a>', obj.evidence_file.url))
        if obj.evidence_file_2:
            links.append(format_html('<a href="{}" target="_blank" style="padding: 6px 12px; background: #059669; color: #fff; border-radius: 6px; text-decoration: none; font-weight: bold;">View Secondary Evidence ↗</a>', obj.evidence_file_2.url))
        return format_html(''.join(links)) if links else 'No evidence files uploaded.'
    evidence_preview.short_description = 'Evidence Documents'

    def mark_under_investigation(self, request, queryset):
        queryset.update(status=CrimeReport.Status.UNDER_INVESTIGATION)
        self.message_user(request, f"{queryset.count()} reports marked as Under Active Investigation.")
    mark_under_investigation.short_description = "Mark Under Active Investigation"

    def escalate_to_authorities(self, request, queryset):
        queryset.update(status=CrimeReport.Status.ESCALATED_AUTHORITIES)
        self.message_user(request, f"{queryset.count()} reports escalated to Law Enforcement (Police / EFCC).")
    escalate_to_authorities.short_description = "Escalate to Law Enforcement (Police / EFCC)"

    def mark_action_taken(self, request, queryset):
        queryset.update(status=CrimeReport.Status.ACTION_TAKEN)
        self.message_user(request, f"{queryset.count()} reports marked as Action Taken.")
    mark_action_taken.short_description = "Mark as Action Taken (Suspended Account / Delisted Property)"

    def mark_resolved(self, request, queryset):
        now = timezone.now()
        queryset.update(status=CrimeReport.Status.RESOLVED, resolved_at=now)
        self.message_user(request, f"{queryset.count()} reports marked as Resolved.")
    mark_resolved.short_description = "Mark as Resolved"

    def dismiss_report(self, request, queryset):
        queryset.update(status=CrimeReport.Status.DISMISSED)
        self.message_user(request, f"{queryset.count()} reports marked as Dismissed.")
    dismiss_report.short_description = "Dismiss Reports"
