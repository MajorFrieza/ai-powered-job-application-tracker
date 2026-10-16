from django.utils import timezone
from rest_framework import serializers


APPLICATION_STATUSES = ('Applied', 'Interview', 'Offer', 'Rejected')


class ApplicationSerializer(serializers.Serializer):
    id = serializers.CharField(source='_id', read_only=True)
    company = serializers.CharField(max_length=120)
    role = serializers.CharField(max_length=120)
    job_link = serializers.URLField(required=False, allow_blank=True, default='')
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    job_description = serializers.CharField(required=False, allow_blank=True, max_length=20000, default='')
    ai_analysis = serializers.JSONField(read_only=True, required=False, allow_null=True)
    date_applied = serializers.DateField(default=timezone.localdate)
    status = serializers.ChoiceField(choices=APPLICATION_STATUSES, default='Applied')
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ApplicationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=APPLICATION_STATUSES)


class JobDescriptionSerializer(serializers.Serializer):
    job_description = serializers.CharField(max_length=20000, allow_blank=False, trim_whitespace=True)


class AnalysisResultSerializer(serializers.Serializer):
    summary = serializers.CharField(max_length=1200)
    required_skills = serializers.ListField(
        child=serializers.CharField(max_length=100),
        max_length=20,
    )
    skills_to_highlight = serializers.ListField(
        child=serializers.CharField(max_length=100),
        max_length=20,
    )
