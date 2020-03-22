import logging

import re
from lianxi import settings
from django.contrib.auth import login
from django.http import HttpResponseBadRequest
from django.http import HttpResponseServerError
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
# Create your views here.
from django.urls import reverse
from django.views import View
from django_redis import get_redis_connection

from apps.oauth.models import OAuthQQUser
from QQLoginTool.QQtool import OAuthQQ

from apps.oauth.utils import serect_openid, check_openid
from apps.users.models import User

logger = logging.getLogger('django')
class QQLoginView(View):
    def get(self,request):

        code = request.GET.get('code')
        state = request.GET.get('state')

        if code is None:
            return HttpResponseBadRequest('code过期')

        oauthqq = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                          client_secret=settings.QQ_CLIENT_SECRET,
                          redirect_uri=settings.QQ_REDIRECT_URI,
                          state=state)
        token = oauthqq.get_access_token(code)

        openid = oauthqq.get_open_id(token)

        try:
            qquser = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            new_openid = serect_openid(openid)
            return render(request,'oauth_callback.html',context={'openid':new_openid})
        else:
            login(request,qquser.user)

            response = redirect(reverse('contents:index'))
            response.set_cookie('username',qquser.user.username,max_age=3600)
            return response

    def post(self, request):
        mobile = request.POST.get('mobile')
        pwd = request.POST.get('pwd')
        sms_code = request.POST.get('sms_code')
        secret_openid = request.POST.get('openid')
        if not all([mobile, pwd, sms_code, secret_openid]):
            return HttpResponseForbidden('缺少必传参数')
            # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseForbidden('请输入正确的手机号码')
            # 判断密码是否合格
        if not re.match(r'^[0-9A-Za-z]{8,20}$', pwd):
            return HttpResponseForbidden('请输入8-20位的密码')
            # 判断短信验证码是否一致
        redis_conn = get_redis_connection('code')
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        if sms_code_server is None:
            return render(request, 'oauth_callback.html', {'sms_code_errmsg': '无效的短信验证码'})
        if sms_code != sms_code_server.decode():
            return render(request, 'oauth_callback.html', {'sms_code_errmsg': '输入短信验证码有误'})
        openid = check_openid(secret_openid)

        if openid is None:
            return HttpResponseBadRequest('openid错误')
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            user = User.objects.create_user(username=mobile,
                                            password=pwd,
                                            mobile=mobile)
        else:
            if not user.check_password(pwd):
                return HttpResponseBadRequest('密码错误')

        OAuthQQUser.objects.create(user=user, openid=openid)

        login(request, user)

        response = redirect(reverse('contents:index'))

        response.set_cookie('username', user.username, max_age=3600)

        return response
