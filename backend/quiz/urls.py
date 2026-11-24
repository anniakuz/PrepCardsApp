from django.urls import path

from . import views

urlpatterns = [
    path("topics/", views.TopicListView.as_view()),
    path("topics/mine/", views.MyTopicsView.as_view()),
    path("topics/popular/", views.PopularTopicsView.as_view()),
    path("topics/example/", views.ExampleView.as_view()),
    path("topics/<int:pk>/", views.TopicDetailView.as_view()),
    path("topics/<int:pk>/join/", views.TopicJoinView.as_view()),
    path("topics/<int:pk>/questions/", views.TopicQuestionsView.as_view()),
    path("topics/<int:pk>/publish/", views.TopicPublishView.as_view()),
    path("topics/<int:pk>/level/", views.TopicLevelView.as_view()),
    path("topics/<int:topic_id>/active-round/", views.ActiveRoundView.as_view()),
    path("rounds/", views.RoundCreateView.as_view()),
    path("rounds/<int:pk>/", views.RoundDetailView.as_view()),
    path("rounds/<int:pk>/answer/", views.RoundAnswerView.as_view()),
    path("rounds/<int:pk>/abandon/", views.RoundAbandonView.as_view()),
    path("saved/", views.SavedListView.as_view()),
    path("saved/<int:question_id>/", views.SavedDeleteView.as_view()),
    path("questions/<int:pk>/", views.QuestionDetailView.as_view()),
    path("questions/<int:pk>/assistant/", views.AssistantView.as_view()),
    path("stats/", views.StatsView.as_view()),
]
