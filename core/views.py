from django.shortcuts import render
from .forms import CustomAuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy


# Create your views here.
def home(request):
    return render(request, 'home.html' )

class CustomLoginView(LoginView):
    # Use the standard registration path so the template under
    # core/templates/registration/login.html is picked up.
    template_name = 'registration/login.html'
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True  # if already logged in redirect to LOGIN_REDIRECT_URL

    def form_valid(self, form):
        # Standard login first
        resp = super().form_valid(form)
        remember = form.cleaned_data.get('remember_me')
        if remember:
            # 2 weeks expiry
            self.request.session.set_expiry(1209600)  # seconds
        else:
            # expire when user closes browser
            self.request.session.set_expiry(0)
        return resp

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')  # or rely on LOGOUT_REDIRECT_URL in settings