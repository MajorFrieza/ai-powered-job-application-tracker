import logging
import json

from google import genai
from google.genai.errors import APIError
from google.genai.types import GenerateContentConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .serializers import AnalysisResultSerializer


logger = logging.getLogger(__name__)


class AnalysisProviderError(Exception):
    pass


def analyze_job_description(job_description):
    if not settings.GEMINI_API_KEY:
        raise ImproperlyConfigured('Set GEMINI_API_KEY in your .env file to use job description analysis.')

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = f'Analyze this job description:\n\n{job_description}'
    response_schema = {
        'type': 'object',
        'properties': {
            'summary': {'type': 'string'},
            'required_skills': {'type': 'array', 'items': {'type': 'string'}},
            'skills_to_highlight': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': ['summary', 'required_skills', 'skills_to_highlight'],
    }
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=GenerateContentConfig(
                system_instruction=(
                    'Analyze the supplied job description. Return a concise summary under 1200 characters, '
                    'up to 20 required skills, and up to 20 skills a candidate should highlight only when '
                    'their experience supports them. Do not invent candidate experience.'
                ),
                response_mime_type='application/json',
                response_schema=response_schema,
                temperature=0.2,
            ),
        )
    except APIError as error:
        logger.exception('Gemini job description analysis request failed.')
        raise AnalysisProviderError('The AI analysis service could not complete the request.') from error

    content = response.text
    if not content:
        raise AnalysisProviderError('The AI analysis service returned an empty response.')

    try:
        result = json.loads(content)
    except json.JSONDecodeError as error:
        raise AnalysisProviderError('The AI analysis service returned an invalid response.') from error

    serializer = AnalysisResultSerializer(data=result)
    if not serializer.is_valid():
        raise AnalysisProviderError('The AI analysis service returned an unexpected response format.')
    return serializer.validated_data
