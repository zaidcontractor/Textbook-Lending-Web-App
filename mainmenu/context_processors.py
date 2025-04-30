from django.conf import settings

def use_aws_flag(request):
    return {
        'USE_AWS': settings.USE_AWS
    }