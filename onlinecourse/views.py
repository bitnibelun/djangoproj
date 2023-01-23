from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# <HINT> Create a submit view to create an exam submission record for a course enrollment
def submit(request, course_id):
    # Get user and course object, 
    #  then get the associated enrollment object created when the user enrolled the course
    #   (HINT: Enrollment.objects.get(user=..., course=...))
    user_obj = request.user
    course_obj = get_object_or_404(Course, id=course_id)
    enrollment_obj = Enrollment.objects.get(user=user_obj, course=course_obj)

    # Create a submission object referring to the enrollment
    #   (HINT: Submission.objects.create(enrollment=...))
    submission_obj = Submission.objects.create(enrollment=enrollment_obj)

    # Collect the selected choices from exam form
    #   Collect the selected choices from HTTP request object 
    #   (HINT: you could use request.POST to get the payload dictionary, and
    #   get the choice id from the dictionary values, an example code snippet is also provided)
    answers = extract_answers(request)

    # Add each selected choice object to the submission object
    for choice_id in answers:
        choice_obj = Choice.objects.get(id = choice_id)
        submission_obj.choices.add(choice_obj)
    submission_obj.save()  

    # Redirecting to the show_exam_result view with the submission id to show the exam result
    return HttpResponseRedirect(reverse(viewname='onlinecourse:show_exam_result', args=(course_id, submission_obj.id)))


# <HINT> A example method to collect the selected choices from the exam form from the request object
def extract_answers(request):
   submitted_anwsers = []
   for key in request.POST:
       if key.startswith('choice'):
           value = request.POST[key]
           choice_id = int(value)
           submitted_anwsers.append(choice_id)
   return submitted_anwsers


# <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
# you may implement it based on the following logic:
def show_exam_result(request, course_id, submission_id):
    # Get course and submission based on their ids
    course_obj = Course.objects.get(id=course_id)

    # Get the selected choice ids from the submission record
    selected_choices_ids = Submission.objects.get(id=submission_id).choices.all()

    # For each selected choice, check if it is a correct answer or not
    # Cannot resolve keyword 'courses' into field. 
    #   Choices are: choice, content, course_id, course_id_id, grade, id, lesson_id, lesson_id_id
    exam_questions = Question.objects.filter(course_id=course_id)

    score = 0
    total_score = 0
    for question in exam_questions:
        total_score += question.grade
        if question.is_get_score(selected_choices_ids):
            score += question.grade

    context = {}
    context['course'] = course_obj
    context['choices'] = selected_choices_ids
    context['questions'] = exam_questions
    context['grade'] = round(score / total_score * 100)

    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
