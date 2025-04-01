from django.shortcuts import render
from .models import Borrow, Member


def index(request):
    borrows = Borrow.objects.all()
    members = Member.objects.all()
    return render(request, 'personnel/index.html', {'borrows': borrows, 'members': members})


def media_list(request):
    return render(request, 'personnel/media_list.html')

def borrowing_media(request):
    return render(request, 'personnel/borrowing_media.html')

def returning_media(request, borrowing_id):
    return render(request, 'personnel/returning_media.html', {'borrowing_id': borrowing_id})

def add_media(request):
    return render(request, 'personnel/add_media.html')

def media_detail(request):
    return render(request, 'personnel/media_detail.html')

def member_list(request):
    return render(request, 'personnel/member_list.html')

def update_member(request, member_id):
    return render(request, 'personnel/update_member.html', {'member_id': member_id})

def add_member(request):
    return render(request, 'personnel/add_member.html')


def member_detail(request):
   return render(request, 'personnel/member_detail.html')
