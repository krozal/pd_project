from django.shortcuts import render
from django.contrib.auth.views import LoginView
from django.views.generic.edit import FormView

from django.contrib.auth import login
from django.contrib.auth import logout
from django.shortcuts import redirect

from django.urls import reverse_lazy

from django.contrib.auth.decorators import login_required

from django.contrib.auth.forms import UserCreationForm
# Create your views here.

def index(request):
    return render(request, 'index.html')

class CustomLoginView(LoginView):
    template_name = 'login.html'
    fields = '__all__'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard')

def my_logout_view(request):
    logout(request)
    return redirect('login')

class RegisterPage(FormView):
    template_name = 'registration.html'
    form_class = UserCreationForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('login')
    def form_valid(self, form):
        form.save()
        user = form.instance
        login(self.request, user)
        return super().form_valid(form)
    
@login_required(login_url='/login')
def dashboard(request):
    return render(request, 'dashboard.html')
