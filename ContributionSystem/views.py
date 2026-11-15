from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ParentForm, StudentCollectionForm, StudentForm
from .models import Parent, Student, StudentCollection


@login_required
def profile(request):
    return render(request, 'accounts/profile.html')


@login_required
def home(request):
    return render(request, 'home.html')


@login_required
def parent_list(request):
    parents = Parent.objects.all()
    return render(request, "contributions/parent_list.html", {"parents": parents})


@login_required
def parent_create(request):
    form = ParentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("parent-list")
    return render(
        request,
        "contributions/form.html",
        {"form": form, "title": "Add parent", "cancel_url": "parent-list"},
    )


@login_required
def student_list(request):
    students = Student.objects.select_related("parent")
    return render(request, "contributions/student_list.html", {"students": students})


@login_required
def student_create(request):
    form = StudentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        student = form.save(commit=False)
        student.registered_by = request.user
        student.save()
        return redirect("student-list")
    return render(
        request,
        "contributions/form.html",
        {"form": form, "title": "Register student", "cancel_url": "student-list"},
    )


@login_required
def collection_list(request):
    collections = StudentCollection.objects.select_related("student", "recorded_by")
    return render(
        request,
        "contributions/collection_list.html",
        {"collections": collections},
    )


@login_required
def collection_create(request):
    form = StudentCollectionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        collection = form.save(commit=False)
        collection.recorded_by = request.user
        collection.save()
        return redirect("collection-list")
    return render(
        request,
        "contributions/form.html",
        {
            "form": form,
            "title": "Record student collection",
            "cancel_url": "collection-list",
        },
    )
