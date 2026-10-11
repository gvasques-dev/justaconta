from django.urls import path
from . import views

app_name = 'relatorios'

urlpatterns = [
    path('', views.relatorio_mensal, name='relatorio_mensal'),
    path('export/pdf/', views.exportar_dossier_pdf, name='exportar_dossier_pdf'),
    path('export/reembolso/', views.exportar_relatorio_reembolso, name='exportar_reembolso'),
]
