import logging
from datetime import datetime, timezone

from bson import ObjectId
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import redirect, render
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .ai_service import AnalysisProviderError, analyze_job_description
from .forms import ApplicationForm
from .mongo import get_application_collection
from .serializers import (
    APPLICATION_STATUSES,
    AnalysisResultSerializer,
    ApplicationSerializer,
    ApplicationStatusSerializer,
    JobDescriptionSerializer,
)


logger = logging.getLogger(__name__)

DATABASE_ERRORS = (ImproperlyConfigured, ServerSelectionTimeoutError, PyMongoError)


def _database_error_response(error):
    logger.error('MongoDB operation failed: %s', error)
    return Response(
        {'detail': 'The application database is unavailable. Check your MongoDB configuration and try again.'},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _database_error_page(request, error):
    logger.error('MongoDB operation failed: %s', error)
    return render(
        request,
        'applications/database_error.html',
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _owned_application(collection, application_id, user):
    if not ObjectId.is_valid(application_id):
        return None
    return collection.find_one({'_id': ObjectId(application_id), 'owner_id': str(user.pk)})


def _status_counts(collection, owner_id):
    return {
        application_status: collection.count_documents(
            {'owner_id': owner_id, 'status': application_status}
        )
        for application_status in APPLICATION_STATUSES
    }


def dashboard_page(request):
    context = {}
    if request.user.is_authenticated:
        try:
            collection = get_application_collection()
            owner_id = str(request.user.pk)
            context['status_counts'] = _status_counts(collection, owner_id)
            context['total_applications'] = sum(context['status_counts'].values())
            recent = list(
                collection.find({'owner_id': owner_id}).sort('date_applied', -1).limit(5)
            )
            for application in recent:
                application['id'] = str(application['_id'])
            context['recent_applications'] = recent
            context['return_to'] = 'board'
            context['add_form'] = ApplicationForm()
        except DATABASE_ERRORS as error:
            return _database_error_page(request, error)
    return render(request, 'home.html', context)


@login_required
def application_list_page(request):
    try:
        collection = get_application_collection()
        owner_id = str(request.user.pk)
        applications = list(collection.find({'owner_id': owner_id}).sort('date_applied', -1))
        status_counts = _status_counts(collection, owner_id)
    except DATABASE_ERRORS as error:
        return _database_error_page(request, error)
    for application in applications:
        application['id'] = str(application['_id'])
    return render(
        request,
        'applications/list.html',
        {
            'applications': applications,
            'statuses': APPLICATION_STATUSES,
            'status_counts': status_counts,
            'total_applications': len(applications),
            'return_to': 'list',
            'add_form': ApplicationForm(),
        },
    )


@login_required
def kanban_board_page(request):
    try:
        collection = get_application_collection()
        owner_id = str(request.user.pk)
        status_counts = _status_counts(collection, owner_id)
        total_applications = sum(status_counts.values())
    except DATABASE_ERRORS as error:
        return _database_error_page(request, error)
    return render(
        request,
        'applications/board.html',
        {
            'statuses': APPLICATION_STATUSES,
            'status_counts': status_counts,
            'total_applications': total_applications,
            'return_to': 'board',
            'add_form': ApplicationForm(),
        },
    )


@login_required
def application_create_page(request):
    form = ApplicationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        now = datetime.now(timezone.utc)
        document = {
            **form.cleaned_data,
            'date_applied': form.cleaned_data['date_applied'].isoformat(),
            'owner_id': str(request.user.pk),
            'created_at': now,
            'updated_at': now,
        }
        try:
            get_application_collection().insert_one(document)
        except DATABASE_ERRORS as error:
            return _database_error_page(request, error)
        if request.POST.get('return_to') == 'board':
            return redirect('kanban-board')
        return redirect('application-list-page')
    return render(
        request,
        'applications/form.html',
        {'form': form, 'page_title': 'Add application'},
    )


@login_required
def application_edit_page(request, application_id):
    try:
        collection = get_application_collection()
        document = _owned_application(collection, application_id, request.user)
    except DATABASE_ERRORS as error:
        return _database_error_page(request, error)
    if document is None:
        return render(request, 'applications/not_found.html', status=status.HTTP_404_NOT_FOUND)

    form = ApplicationForm(request.POST if request.method == 'POST' else None, initial=document)
    if request.method == 'POST' and form.is_valid():
        updated_at = datetime.now(timezone.utc)
        update = {
            **form.cleaned_data,
            'date_applied': form.cleaned_data['date_applied'].isoformat(),
            'updated_at': updated_at,
        }
        if form.cleaned_data['job_description'] != document.get('job_description', ''):
            update['ai_analysis'] = None
        try:
            collection.update_one(
                {'_id': document['_id'], 'owner_id': str(request.user.pk)},
                {'$set': update},
            )
        except DATABASE_ERRORS as error:
            return _database_error_page(request, error)
        return redirect('application-list-page')
    return render(
        request,
        'applications/form.html',
        {
            'form': form,
            'page_title': 'Edit application',
            'application_id': application_id,
            'analysis': document.get('ai_analysis'),
        },
    )


@login_required
def application_delete_page(request, application_id):
    if request.method != 'POST':
        return redirect('application-list-page')
    try:
        collection = get_application_collection()
        document = _owned_application(collection, application_id, request.user)
        if document is not None:
            collection.delete_one({'_id': document['_id'], 'owner_id': str(request.user.pk)})
    except DATABASE_ERRORS as error:
        return _database_error_page(request, error)
    return redirect('application-list-page')


class ApplicationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            documents = get_application_collection().find({'owner_id': str(request.user.pk)})
            return Response([ApplicationSerializer(document).data for document in documents])
        except (ImproperlyConfigured, ServerSelectionTimeoutError, PyMongoError) as error:
            return _database_error_response(error)

    def post(self, request):
        serializer = ApplicationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        now = datetime.now(timezone.utc)
        document = {
            **serializer.validated_data,
            'owner_id': str(request.user.pk),
            'created_at': now,
            'updated_at': now,
        }
        document['date_applied'] = document['date_applied'].isoformat()

        try:
            result = get_application_collection().insert_one(document)
            document['_id'] = result.inserted_id
            return Response(ApplicationSerializer(document).data, status=status.HTTP_201_CREATED)
        except (ImproperlyConfigured, ServerSelectionTimeoutError, PyMongoError) as error:
            return _database_error_response(error)


class ApplicationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, application_id):
        try:
            collection = get_application_collection()
            document = _owned_application(collection, application_id, request.user)
        except (ImproperlyConfigured, ServerSelectionTimeoutError, PyMongoError) as error:
            return _database_error_response(error)
        if document is None:
            return Response({'detail': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ApplicationSerializer(document).data)

    def put(self, request, application_id):
        try:
            collection = get_application_collection()
            document = _owned_application(collection, application_id, request.user)
        except (ImproperlyConfigured, ServerSelectionTimeoutError, PyMongoError) as error:
            return _database_error_response(error)
        if document is None:
            return Response({'detail': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ApplicationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_at = datetime.now(timezone.utc)
        update = {**serializer.validated_data, 'updated_at': updated_at}
        update['date_applied'] = update['date_applied'].isoformat()
        if serializer.validated_data['job_description'] != document.get('job_description', ''):
            update['ai_analysis'] = None
        try:
            collection.update_one(
                {'_id': document['_id'], 'owner_id': str(request.user.pk)},
                {'$set': update},
            )
        except (ImproperlyConfigured, ServerSelectionTimeoutError, PyMongoError) as error:
            return _database_error_response(error)
        document.update(update)
        return Response(ApplicationSerializer(document).data)

    def delete(self, request, application_id):
        try:
            collection = get_application_collection()
            document = _owned_application(collection, application_id, request.user)
            if document is None:
                return Response({'detail': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)
            collection.delete_one({'_id': document['_id'], 'owner_id': str(request.user.pk)})
        except (ImproperlyConfigured, ServerSelectionTimeoutError, PyMongoError) as error:
            return _database_error_response(error)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplicationStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, application_id):
        serializer = ApplicationStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            collection = get_application_collection()
            document = _owned_application(collection, application_id, request.user)
            if document is None:
                return Response({'detail': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)
            updated_at = datetime.now(timezone.utc)
            update = {'status': serializer.validated_data['status'], 'updated_at': updated_at}
            collection.update_one(
                {'_id': document['_id'], 'owner_id': str(request.user.pk)},
                {'$set': update},
            )
        except (ImproperlyConfigured, ServerSelectionTimeoutError, PyMongoError) as error:
            return _database_error_response(error)

        document.update(update)
        return Response(ApplicationSerializer(document).data)


class ApplicationAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, application_id):
        description_serializer = JobDescriptionSerializer(data=request.data)
        if not description_serializer.is_valid():
            return Response(description_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            collection = get_application_collection()
            document = _owned_application(collection, application_id, request.user)
        except DATABASE_ERRORS as error:
            return _database_error_response(error)
        if document is None:
            return Response({'detail': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            analysis = analyze_job_description(description_serializer.validated_data['job_description'])
        except ImproperlyConfigured as error:
            logger.error('AI analysis configuration error: %s', error)
            return Response(
                {'detail': str(error)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AnalysisProviderError as error:
            return Response({'detail': str(error)}, status=status.HTTP_502_BAD_GATEWAY)

        result_serializer = AnalysisResultSerializer(data=analysis)
        result_serializer.is_valid(raise_exception=True)
        updated_at = datetime.now(timezone.utc)
        update = {
            'job_description': description_serializer.validated_data['job_description'],
            'ai_analysis': result_serializer.validated_data,
            'updated_at': updated_at,
        }
        try:
            collection.update_one(
                {'_id': document['_id'], 'owner_id': str(request.user.pk)},
                {'$set': update},
            )
        except DATABASE_ERRORS as error:
            return _database_error_response(error)

        return Response(update, status=status.HTTP_200_OK)

# Create your views here.
