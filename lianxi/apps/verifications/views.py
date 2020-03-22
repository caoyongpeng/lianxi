from django.http import HttpResponse,HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from django.views import View


class ImageCodeView(View):
    def get(self,request,uuid):
        from libs.captcha.captcha import captcha
        text,image = captcha.generate_captcha()
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection('code')
        redis_conn.setex('img_%s'%uuid,120,text)
        return HttpResponse(image,content_type='image/jpeg')

class SmsCodeView(View):
    def get(self,request,mobile):
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection('code')
        send_flag = redis_conn.get('send_flag_%s'%mobile)
        if send_flag:
            return HttpResponseBadRequest('发送短信过于频繁')
        image_code = request.GET.get('image_code')
        image_code_id = request.GET.get('image_code_id')

        if not all([image_code,image_code_id]):
            return HttpResponseBadRequest('参数不全')
        redis_text = redis_conn.get('img_%s'%image_code_id)
        if redis_text is None:
            return HttpResponseBadRequest('图片验证码过期')
        if redis_text.decode().lower() != image_code.lower():
            return HttpResponseBadRequest('验证码不一致')
        from random import randint
        sms_code = '%06d'%randint(0,999999)
        pl = redis_conn.pipeline()
        pl.setex('sms_%s'%mobile,300,sms_code)
        pl.setex('send_flag_%s'%mobile,60,1)
        pl.execute()
        from celery_tasks.sms.tasks import send_sms_code
        send_sms_code.delay(mobile, sms_code)
        return JsonResponse({'msg':'ok','code':'0'})
