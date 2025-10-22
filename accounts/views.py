from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .forms import CustomUserCreationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

# Create your views here.
# yeh signup functions ka code hain,

def home_view(request):
  return render(request, 'accounts/home.html')
def signup_view(request):
  if request.method == 'POST':
    form = CustomUserCreationForm(request.POST)
    if form.is_valid():
      user = form.save() # yaha per database me data save ho jayega... 
      login(request, user)  #user ko login karne ke liye built in login form ko request bhejenege 
      return redirect('accounts/profile')
    
  else:
    form = CustomUserCreationForm()  # <<< yeh zaroori hain GET request ke liye...
  return render(request, 'accounts/signup.html', {'form': form})

# yeh jab aage jaayega dashboard per jab login required hi hoga...
@login_required

def profile_view(request):
  return render(request, 'accounts/profile.html', {})

# @require_POST
def logout_view(request):
  logout(request)
  # messages.success(request, "you're Successfully Logout")
  return redirect('leads:leads_list')
  
  