from django.urls import path

from . import views

urlpatterns = [
    path("mentors/", views.MentorListView.as_view()),
    path("mentors/stats/", views.MentorStatsView.as_view()),
    path("mentors/availability/", views.AvailabilityView.as_view()),
    path("mentoring/notifications/", views.NotificationsView.as_view()),
    path("enrollments/", views.EnrollmentListView.as_view()),
    path("enrollments/<int:pk>/", views.EnrollmentDetailView.as_view()),
    path("enrollments/<int:pk>/messages/", views.MessageListView.as_view()),
    path("enrollments/<int:pk>/read/", views.MarkReadView.as_view()),
    path("enrollments/<int:pk>/stats/", views.StudentDataView.as_view(kind="stats")),
    path("enrollments/<int:pk>/reviews/", views.StudentDataView.as_view(kind="reviews")),
    path("enrollments/<int:pk>/<str:action>/", views.EnrollmentActionView.as_view()),
]
