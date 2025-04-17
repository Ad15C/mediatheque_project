
def handle_error(request, message, redirect_url='media_list'):
    messages.error(request, message)
    return redirect(redirect_url)
