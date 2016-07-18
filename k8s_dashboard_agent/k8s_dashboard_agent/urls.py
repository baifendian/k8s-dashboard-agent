from django.conf.urls import patterns, include, url



urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'k8s_dashboard_agent.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^', include('kd_agent.urls'))
)
