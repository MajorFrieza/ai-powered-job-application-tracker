"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from applications.views import (
    application_create_page,
    application_delete_page,
    application_edit_page,
    application_list_page,
    dashboard_page,
    kanban_board_page,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('applications/', application_list_page, name='application-list-page'),
    path('board/', kanban_board_page, name='kanban-board'),
    path('applications/new/', application_create_page, name='application-create-page'),
    path('applications/<str:application_id>/edit/', application_edit_page, name='application-edit-page'),
    path('applications/<str:application_id>/delete/', application_delete_page, name='application-delete-page'),
    path('api/', include('applications.urls')),
    path('accounts/', include('accounts.urls')),
    path('', dashboard_page, name='home'),
]
