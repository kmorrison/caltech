from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'caltech.views.home', name='home'),
    # url(r'^caltech/', include('caltech.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    url(r'^index/', 'jeeves.views.index'),
    url(r'^new_scheduler/', 'jeeves.views.new_scheduler'),
    url(r'^scheduler/', 'jeeves.views.scheduler'),
    url(r'^scheduler_post/', 'jeeves.views.scheduler_post'),
    url(r'^interview_post/', 'jeeves.views.interview_post'),
    url(r'^find_times/', 'jeeves.views.find_times'),
    url(r'^find_times_post/', 'jeeves.views.find_times_post'),
    url(r'^tracker/', 'jeeves.views.tracker'),
)
