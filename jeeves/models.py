from django.db import models
from django.contrib import admin

class Interviewer(models.Model):

    name = models.CharField(max_length=256)
    domain = models.CharField(max_length=256)

    def __unicode__(self):
        return self.name

    @property
    def address(self):
        return "%s@%s" % (self.name, self.domain)

    class Meta:
        ordering = ('name',)


class Requisition(models.Model):

    name = models.CharField(max_length=256)
    interviewers = models.ManyToManyField(Interviewer, related_name='requisitions')

    def __unicode__(self):
        return self.name

class RequisitionInline(admin.TabularInline):
    model = Requisition.interviewers.through

class InterviewerAdmin(admin.ModelAdmin):
    inlines = [RequisitionInline]

class RequisitionAdmin(admin.ModelAdmin):
    inlines = [RequisitionInline]
    exclude = ('interviewers',)

admin.site.register(Interviewer, InterviewerAdmin)
admin.site.register(Requisition, RequisitionAdmin)
