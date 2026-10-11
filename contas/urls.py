from django.urls import path
from . import views

app_name = 'contas'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('contas/', views.ContaListView.as_view(), name='lista'),
    path('contas/nova/', views.ContaCreateView.as_view(), name='criar'),
    path('contas/<uuid:pk>/editar/', views.ContaUpdateView.as_view(), name='editar'),
    path('contas/<uuid:pk>/excluir/', views.ContaDeleteView.as_view(), name='excluir'),
    path('recibos/novo/', views.recibo_novo, name='recibo_novo'),
    path('despesas/nova/', views.despesa_nova, name='despesa_nova'),
    path('transacoes/', views.transacao_lista, name='transacao_lista'),
    path('transacoes/nova/', views.transacao_create, name='transacao_nova'),
    path('transacoes/<uuid:pk>/editar/', views.transacao_update, name='transacao_editar'),
    path('transacoes/<uuid:pk>/excluir/', views.transacao_delete, name='transacao_excluir'),
    path('transacoes/<uuid:pk>/', views.transacao_detail, name='transacao_detalhe'),
]
