from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from user.models import Ticket
from django.contrib.auth import logout

def is_admin(user):
    return user.is_staff


def admin_login(request):
    from django.contrib.auth import authenticate, login
    from django.contrib import messages

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user and user.is_staff:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Invalid admin credentials")

    return render(request, "Admin/admin_login.html")


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    tickets = Ticket.objects.all().order_by("-created_at")

    total = tickets.count()
    resolved = tickets.filter(status="Resolved").count()
    pending = tickets.filter(status="Pending").count()
    in_progress = tickets.filter(status="In Progress").count()

    return render(request, "admin_panel/dashboard.html", {
        "tickets": tickets,
        "total_count": total,
        "resolved_count": resolved,
        "pending_count": pending,
        "in_progress_count": in_progress
    })

@login_required
@user_passes_test(is_admin)
def update_ticket(request, id):
    if request.method == "POST":
        ticket = Ticket.objects.get(id=id)
        ticket.status = request.POST.get("status")
        ticket.save()

        return JsonResponse({"success": True})

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    tickets = Ticket.objects.all().order_by("-id")

    return render(request, "Admin/dashboard.html", {
        "tickets": tickets
    })

@login_required
@user_passes_test(is_admin)
def create_staff(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = User.objects.create_user(
            username=username,
            password=password
        )
        user.is_staff = True
        user.save()

        return redirect("admin_dashboard")

    return render(request, "Admin/create_staff.html")

def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        User.objects.create_user(username=username, password=password)
        return redirect("login")

    return render(request, "register.html")


def logout_view(request):
    logout(request)
    return redirect('admin_dashboard') 

