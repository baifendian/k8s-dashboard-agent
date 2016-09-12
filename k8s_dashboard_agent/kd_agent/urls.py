from django.conf.urls import patterns, url

from kd_agent import views

urlpatterns = patterns('',

    url(r'^api/v1/clusterinfo/cpu/(?P<minutes>\d{1,5})',views.get_cluster_cpu_info ),
    url(r'^api/v1/clusterinfo/memory/(?P<minutes>\d{1,5})',views.get_cluster_memory_info ),
    url(r'^api/v1/clusterinfo/network/(?P<minutes>\d{1,5})',views.get_cluster_network_info ),
    url(r'^api/v1/clusterinfo/filesystem/(?P<minutes>\d{1,5})',views.get_cluster_filesystem_info ),

)
