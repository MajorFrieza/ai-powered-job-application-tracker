from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from bson import ObjectId
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .ai_service import AnalysisProviderError, analyze_job_description


class AiServiceTests(TestCase):
    @override_settings(GEMINI_API_KEY='test-key', GEMINI_MODEL='test-model')
    @patch('applications.ai_service.genai.Client')
    def test_analysis_uses_one_structured_provider_call(self, gemini_client):
        gemini_client.return_value.models.generate_content.return_value = SimpleNamespace(
            text=(
                '{"summary":"Build APIs.","required_skills":["Python"],'
                '"skills_to_highlight":["Django"]}'
            )
        )

        result = analyze_job_description('Python backend engineer')

        self.assertEqual(result['summary'], 'Build APIs.')
        gemini_client.assert_called_once_with(api_key='test-key')
        gemini_client.return_value.models.generate_content.assert_called_once()
        call = gemini_client.return_value.models.generate_content.call_args.kwargs
        self.assertEqual(call['model'], 'test-model')
        self.assertEqual(call['config'].response_mime_type, 'application/json')
        self.assertIn('required_skills', call['config'].response_schema['properties'])
        self.assertIn('Python backend engineer', call['contents'])

    @override_settings(GEMINI_API_KEY='test-key', GEMINI_MODEL='test-model')
    @patch('applications.ai_service.genai.Client')
    def test_analysis_rejects_unexpected_provider_response(self, gemini_client):
        gemini_client.return_value.models.generate_content.return_value = SimpleNamespace(
            text='{"summary":"Incomplete"}'
        )

        with self.assertRaises(AnalysisProviderError):
            analyze_job_description('Python backend engineer')


class ApplicationApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='applicant', password='StrongPassword!42')
        self.client.force_login(self.user)

    @patch('applications.views.get_application_collection')
    def test_list_filters_by_logged_in_user(self, get_collection):
        get_collection.return_value.find.return_value = []

        response = self.client.get(reverse('application-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        get_collection.return_value.find.assert_called_once_with({'owner_id': str(self.user.pk)})

    @patch('applications.views.get_application_collection')
    def test_create_saves_owner_and_returns_application(self, get_collection):
        application_id = ObjectId()
        get_collection.return_value.insert_one.return_value.inserted_id = application_id

        response = self.client.post(
            reverse('application-list'),
            {'company': 'Example Co', 'role': 'Engineer', 'date_applied': '2026-10-16'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['id'], str(application_id))
        saved_document = get_collection.return_value.insert_one.call_args.args[0]
        self.assertEqual(saved_document['owner_id'], str(self.user.pk))
        self.assertEqual(saved_document['date_applied'], '2026-10-16')

    @patch('applications.views.get_application_collection')
    def test_invalid_application_is_rejected(self, get_collection):
        response = self.client.post(
            reverse('application-list'),
            {'company': '', 'role': 'Engineer', 'date_applied': 'not-a-date'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        get_collection.assert_not_called()

    @patch('applications.views.get_application_collection')
    def test_cannot_retrieve_another_users_application(self, get_collection):
        application_id = ObjectId()
        get_collection.return_value.find_one.return_value = None

        response = self.client.get(reverse('application-detail', args=[application_id]))

        self.assertEqual(response.status_code, 404)
        get_collection.return_value.find_one.assert_called_once_with(
            {'_id': application_id, 'owner_id': str(self.user.pk)}
        )

    @patch('applications.views.get_application_collection')
    def test_put_updates_owned_application(self, get_collection):
        application_id = ObjectId()
        document = {
            '_id': application_id,
            'owner_id': str(self.user.pk),
            'company': 'Old Co',
            'role': 'Engineer',
            'job_link': '',
            'notes': '',
            'date_applied': '2026-10-16',
            'status': 'Applied',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }
        get_collection.return_value.find_one.return_value = document

        response = self.client.put(
            reverse('application-detail', args=[application_id]),
            {'company': 'New Co', 'role': 'Senior Engineer', 'date_applied': date.today().isoformat()},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['company'], 'New Co')
        get_collection.return_value.update_one.assert_called_once()

    @patch('applications.views.get_application_collection')
    def test_delete_removes_owned_application(self, get_collection):
        application_id = ObjectId()
        get_collection.return_value.find_one.return_value = {'_id': application_id}

        response = self.client.delete(reverse('application-detail', args=[application_id]))

        self.assertEqual(response.status_code, 204)
        get_collection.return_value.delete_one.assert_called_once_with(
            {'_id': application_id, 'owner_id': str(self.user.pk)}
        )

    def test_api_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse('application-list'))

        self.assertEqual(response.status_code, 403)

    @patch('applications.views.get_application_collection')
    def test_status_update_changes_only_owned_application(self, get_collection):
        application_id = ObjectId()
        get_collection.return_value.find_one.return_value = {
            '_id': application_id,
            'owner_id': str(self.user.pk),
            'company': 'Acme',
            'role': 'Engineer',
            'job_link': '',
            'notes': '',
            'date_applied': '2026-10-16',
            'status': 'Applied',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }

        response = self.client.patch(
            reverse('application-status', args=[application_id]),
            {'status': 'Interview'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'Interview')
        get_collection.return_value.update_one.assert_called_once()
        self.assertEqual(
            get_collection.return_value.update_one.call_args.args[0],
            {'_id': application_id, 'owner_id': str(self.user.pk)},
        )

    @patch('applications.views.analyze_job_description')
    @patch('applications.views.get_application_collection')
    def test_analyze_saves_description_and_result_to_owned_application(
        self,
        get_collection,
        analyze_job_description,
    ):
        application_id = ObjectId()
        get_collection.return_value.find_one.return_value = {
            '_id': application_id,
            'owner_id': str(self.user.pk),
            'job_description': '',
        }
        analyze_job_description.return_value = {
            'summary': 'Build web APIs.',
            'required_skills': ['Python', 'Django'],
            'skills_to_highlight': ['REST APIs'],
        }

        response = self.client.post(
            reverse('application-analyze', args=[application_id]),
            {'job_description': 'We need a Python engineer with Django experience.'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['ai_analysis']['summary'], 'Build web APIs.')
        analyze_job_description.assert_called_once_with(
            'We need a Python engineer with Django experience.'
        )
        get_collection.return_value.update_one.assert_called_once()
        update_filter, update_command = get_collection.return_value.update_one.call_args.args
        self.assertEqual(update_filter, {'_id': application_id, 'owner_id': str(self.user.pk)})
        self.assertEqual(
            update_command['$set']['job_description'],
            'We need a Python engineer with Django experience.',
        )

    @patch('applications.views.analyze_job_description')
    @patch('applications.views.get_application_collection')
    def test_analyze_rejects_blank_description_without_calling_provider(
        self,
        get_collection,
        analyze_job_description,
    ):
        response = self.client.post(
            reverse('application-analyze', args=[ObjectId()]),
            {'job_description': '   '},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        get_collection.assert_not_called()
        analyze_job_description.assert_not_called()

    @patch('applications.views.analyze_job_description')
    @patch('applications.views.get_application_collection')
    def test_analyze_does_not_call_provider_for_another_users_application(
        self,
        get_collection,
        analyze_job_description,
    ):
        get_collection.return_value.find_one.return_value = None

        response = self.client.post(
            reverse('application-analyze', args=[ObjectId()]),
            {'job_description': 'A valid job description.'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 404)
        analyze_job_description.assert_not_called()

    @patch('applications.views.get_application_collection')
    @override_settings(GEMINI_API_KEY=None)
    def test_analyze_reports_missing_api_key(self, get_collection):
        application_id = ObjectId()
        get_collection.return_value.find_one.return_value = {'_id': application_id}

        response = self.client.post(
            reverse('application-analyze', args=[application_id]),
            {'job_description': 'A valid job description.'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 503)
        self.assertContains(response, 'GEMINI_API_KEY', status_code=503)


class ApplicationPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pageuser', password='StrongPassword!42')
        self.client.force_login(self.user)

    @patch('applications.views.get_application_collection')
    def test_list_page_shows_only_current_users_applications(self, get_collection):
        application_id = ObjectId()
        get_collection.return_value.find.return_value.sort.return_value = [
            {
                '_id': application_id,
                'company': 'Acme',
                'role': 'Engineer',
                'date_applied': '2026-10-16',
                'status': 'Applied',
                'job_link': '',
                'notes': '',
            }
        ]

        response = self.client.get(reverse('application-list-page'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Acme')
        self.assertContains(response, f'/applications/{application_id}/edit/')
        get_collection.return_value.find.assert_called_once_with({'owner_id': str(self.user.pk)})

    @patch('applications.views.get_application_collection')
    def test_create_page_validates_and_saves_owned_application(self, get_collection):
        response = self.client.post(
            reverse('application-create-page'),
            {
                'company': 'Acme',
                'role': 'Engineer',
                'date_applied': '2026-10-16',
                'status': 'Applied',
            },
        )

        self.assertRedirects(response, reverse('application-list-page'))
        saved_document = get_collection.return_value.insert_one.call_args.args[0]
        self.assertEqual(saved_document['owner_id'], str(self.user.pk))
        self.assertEqual(saved_document['date_applied'], '2026-10-16')

    @patch('applications.views.get_application_collection')
    def test_create_modal_returns_to_requested_application_view(self, get_collection):
        response = self.client.post(
            reverse('application-create-page'),
            {
                'company': 'Acme',
                'role': 'Engineer',
                'date_applied': '2026-10-16',
                'status': 'Interview',
                'return_to': 'board',
            },
        )

        self.assertRedirects(response, reverse('kanban-board'), fetch_redirect_response=False)
        get_collection.return_value.insert_one.assert_called_once()

    @patch('applications.views.get_application_collection')
    def test_create_page_renders_validation_errors(self, get_collection):
        response = self.client.post(
            reverse('application-create-page'),
            {'company': '', 'role': '', 'date_applied': 'bad-date', 'status': 'Unknown'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter a valid date')
        get_collection.assert_not_called()

    @patch('applications.views.get_application_collection')
    def test_edit_page_updates_only_owned_application(self, get_collection):
        application_id = ObjectId()
        get_collection.return_value.find_one.return_value = {
            '_id': application_id,
            'owner_id': str(self.user.pk),
            'company': 'Old Co',
            'role': 'Engineer',
            'date_applied': '2026-10-16',
            'status': 'Applied',
            'job_link': '',
            'notes': '',
        }

        response = self.client.post(
            reverse('application-edit-page', args=[application_id]),
            {
                'company': 'New Co',
                'role': 'Senior Engineer',
                'date_applied': '2026-10-17',
                'status': 'Interview',
            },
        )

        self.assertRedirects(response, reverse('application-list-page'))
        get_collection.return_value.update_one.assert_called_once()
        self.assertEqual(
            get_collection.return_value.update_one.call_args.args[0],
            {'_id': application_id, 'owner_id': str(self.user.pk)},
        )

    @patch('applications.views.get_application_collection')
    def test_delete_page_deletes_owned_application(self, get_collection):
        application_id = ObjectId()
        get_collection.return_value.find_one.return_value = {'_id': application_id}

        response = self.client.post(reverse('application-delete-page', args=[application_id]))

        self.assertRedirects(response, reverse('application-list-page'))
        get_collection.return_value.delete_one.assert_called_once_with(
            {'_id': application_id, 'owner_id': str(self.user.pk)}
        )

    def test_application_pages_require_login(self):
        self.client.logout()

        response = self.client.get(reverse('application-list-page'))

        self.assertRedirects(response, f'{reverse("login")}?next={reverse("application-list-page")}')

    @patch('applications.views.get_application_collection')
    def test_board_page_renders_status_columns(self, get_collection):
        get_collection.return_value.count_documents.return_value = 0

        response = self.client.get(reverse('kanban-board'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Applied')
        self.assertContains(response, 'Interview')
        self.assertContains(response, 'Offer')
        self.assertContains(response, 'Rejected')
        self.assertContains(response, 'applications/board.js')
        self.assertContains(response, 'Your next chapter.')
        self.assertContains(response, 'add-application-modal')
        self.assertContains(response, 'data-status-filter')

    @patch('applications.views.get_application_collection')
    def test_list_page_shows_status_filter_and_add_dialog(self, get_collection):
        get_collection.return_value.find.return_value.sort.return_value = []
        get_collection.return_value.count_documents.return_value = 0

        response = self.client.get(reverse('application-list-page'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No applications yet')
        self.assertContains(response, 'add-application-modal')
        self.assertContains(response, 'data-status-filter')

    @patch('applications.views.get_application_collection')
    def test_dashboard_counts_applications_by_status_for_current_user(self, get_collection):
        counts = {'Applied': 2, 'Interview': 1, 'Offer': 1, 'Rejected': 0}
        get_collection.return_value.count_documents.side_effect = (
            counts[application_status] for application_status in ('Applied', 'Interview', 'Offer', 'Rejected')
        )

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['status_counts'], counts)
        self.assertEqual(response.context['total_applications'], 4)
        self.assertContains(response, 'applications total')
        self.assertEqual(get_collection.return_value.count_documents.call_count, 4)
        self.assertEqual(
            get_collection.return_value.count_documents.call_args_list[0].args[0],
            {'owner_id': str(self.user.pk), 'status': 'Applied'},
        )

    def test_anonymous_homepage_shows_landing_page_without_database(self):
        self.client.logout()

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your next chapter starts here')
        self.assertNotIn('status_counts', response.context)

    @patch('applications.views.get_application_collection')
    def test_edit_page_shows_saved_analysis(self, get_collection):
        application_id = ObjectId()
        get_collection.return_value.find_one.return_value = {
            '_id': application_id,
            'owner_id': str(self.user.pk),
            'company': 'Acme',
            'role': 'Engineer',
            'date_applied': '2026-10-16',
            'status': 'Applied',
            'job_link': '',
            'notes': '',
            'job_description': 'A description',
            'ai_analysis': {
                'summary': 'Build APIs.',
                'required_skills': ['Python'],
                'skills_to_highlight': ['Django'],
            },
        }

        response = self.client.get(reverse('application-edit-page', args=[application_id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Build APIs.')
        self.assertContains(response, 'Analyze with AI')
