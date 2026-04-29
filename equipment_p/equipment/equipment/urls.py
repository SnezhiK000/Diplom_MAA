from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from equip import views

urlpatterns = [
    # Главная страница
    path('', views.index, name='index'),

    # Авторизация
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('registration/', views.registration_view, name='registration_view'),

    # Сотрудник (заказчик)
    path('customer/', views.CustomerRequestListView.as_view(), name='show_customer'),
    path('create-request-customer/', views.create_request_customer, name='create_request_customer'),
    path('delete-request-customer/<int:request_id>/', views.delete_request_customer, name='delete_request_customer'),

    # Техник
    path('technician/', views.TechnicianRequestListView.as_view(), name='show_technician'),
    path('new-requests/', views.show_new_requests, name='show_new_requests'),
    path('my-requests/', views.my_requests, name='my_requests'),
    path('create-request-technician/', views.create_request_technician, name='create_request_technician'),
    path('edit-request/<int:request_id>/', views.edit_request, name='edit_request'),
    path('delete-request-technician/<int:request_id>/', views.delete_request_technician, name='delete_request_technician'),
    path('deleted-requests/', views.show_deleted_requests, name='show_deleted_requests'),
    path('restore-request/<int:request_id>/', views.restore_request, name='restore_request'),

    # Оборудование
    path('equipment/', views.EquipmentListView.as_view(), name='show_equipment'),
    path('equipment-history/<int:inventory_number>/', views.show_equipment_history, name='show_equipment_history'),
    path('create-equipment/', views.create_equipment, name='create_equipment'),
    path('edit-equipment/<int:inventory_number>/', views.edit_equipment, name='edit_equipment'),
    path('equipment-costs/', views.equipment_costs, name='equipment_costs'),path('equipment/', views.EquipmentListView.as_view(), name='show_equipment'),
    path('delete-equipment/<int:inventory_number>/', views.delete_equipment, name='delete_equipment'),
    path('deleted-equipment/', views.show_deleted_equipment, name='show_deleted_equipment'),
    path('restore-equipment/<int:inventory_number>/', views.restore_equipment, name='restore_equipment'),
    path('delete-equipment-permanent/<int:inventory_number>/', views.delete_equipment_permanent, name='delete_equipment_permanent'),
    # Руководитель
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/equipment-costs/', views.manager_equipment_costs, name='manager_equipment_costs'),

    # АДМИНИСТРАТОР
    path('show-admin/', views.show_admin, name='show_admin'),
    path('admin/create-employee/', views.create_employee_admin, name='create_employee_admin'),
    path('admin/edit-employee/<int:employee_id>/', views.edit_employee_admin, name='edit_employee_admin'),
    path('admin/delete-employee/<int:employee_id>/', views.delete_employee_admin, name='delete_employee_admin'),
    path('admin/deleted-employees/', views.show_deleted_employees, name='show_deleted_employees'),
    path('admin/restore-employee/<int:employee_id>/', views.restore_employee, name='restore_employee'),
    path('admin/delete-employee-permanent/<int:employee_id>/', views.delete_employee_permanent, name='delete_employee_permanent'),

    # AJAX создание справочников
    path('ajax/create-type/', views.create_equipment_type, name='create_equipment_type'),
    path('ajax/create-model/', views.create_equipment_model, name='create_equipment_model'),
    path('ajax/create-office/', views.create_office, name='create_office'),
    path('ajax/create-manufacturer/', views.create_manufacturer, name='create_manufacturer'),
    path('ajax/create-warranty/', views.create_warranty, name='create_warranty'),

    path('my-profile/', views.show_my_profile, name='show_my_profile'),

    path('print-completed/<int:request_id>/', views.print_completed_request, name='print_completed_request'),
    path('print-new/<int:request_id>/', views.print_new_request, name='print_new_request'),

]

# Подключение медиа файлов в режиме отладки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)