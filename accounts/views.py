from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import RegistrationForm


class SignUpView(CreateView):
    form_class = RegistrationForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('login')
