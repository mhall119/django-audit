from django.db import models
from django.contrib.auth.models import User
import audituser

class AuditRecord(models.Model):
    audit_date = models.DateTimeField("Date", auto_now_add=True)
    user = models.ForeignKey(User, null=True)
    app_name = models.CharField("Application", max_length = 50)
    model_name = models.CharField("Model", max_length = 50)
    model_id = models.PositiveIntegerField("Model ID")
    field_name = models.CharField("Field", max_length = 50)
    old_val = models.CharField("From", max_length = 255, blank=True, null=True)
    new_val = models.CharField("To", max_length = 255, blank=True, null=True)

    class Meta:
        ordering = ['-audit_date']
        db_table = 'audit_log'
        verbose_name = "Audit Record"
        
    def __unicode__(self):
        return "%s.%s[%s].%s: %s -> %s" % (self.app_name, self.model_name, self.model_id, self.field_name, self.old_val, self.new_val)
    
class AuditModel(models.Model):
    "Base Model that offer automatic Auditing on calls to save() and disabled delete()"
    
    class Meta:
        abstract = True

    audit_ignore = []
    audit_censor = []
    
    def save(self, force_insert=False, force_update=False):
        # add auditing functionality when a sub-class is saved
        
        # Get the currently saved value for the model
        # Create a new model of the same class if no previous instance exist
        if (self.id is not None and self.id > 0):
            try:
                old = self.__class__.objects.get(id=self.id)
            except:
                old = self.__class__()
        else:
            old = self.__class__()
            
        # model is saved prior to auditing, to ensure that we don't 
        # record a change before it is made
        super(AuditModel, self).save(force_insert, force_update)

        for f in self._get_audit_fields():
            try:
                oldval = getattr(old, f, None)
            except:
                oldval = None
            newval = getattr(self, f, None)

            # For some reason oldval will be an int, when the field is infact a 
            # boolean, so this will force oldval to be the right type
            if isinstance(newval, bool) and isinstance(oldval, int):
                oldval = bool(oldval)
                
            if (isinstance(oldval, models.Model)):
                oldval = getattr(oldval, 'id', oldval)
            if (isinstance(newval, models.Model)):
                newval = getattr(newval, 'id', newval)
    
            if ((oldval and oldval.__str__().strip() != '') or (newval and newval.__str__().strip() != '')) and not (oldval and newval and oldval.__str__().strip() == newval.__str__().strip()):
                if f in self.audit_censor:
                    self._recordChange(f, '*****', '*****')
                else:
                    self._recordChange(f, oldval, newval)
        
    def delete(self):
        if (self.id is not None and self.id > 0):
            old = self.__class__.objects.get(id=self.id)
            for f in old._get_audit_fields():
                oldval = getattr(old, f, None)
                if oldval is not None:
                    self._recordChange(f, oldval, None)
        super(AuditModel, self).delete()
    
    def auditLog(self):
        return AuditRecord.objects.filter(app_name=self._meta.app_label, model_name=self.__class__.__name__, model_id=self.id)

    def _recordChange(self, fieldname, oldval, newval):
        rec = AuditRecord()
        rec.user = audituser.get_current_user() 
        rec.app_name = self._meta.app_label;
        rec.model_name = self.__class__.__name__
        rec.model_id = self.id
        rec.field_name = fieldname[0:50]
        rec.old_val = str(oldval)[0:255]
        rec.new_val = str(newval)[0:255]
        
        rec.save()
        
    def _get_audit_fields(self):
        "Get a list of fields from a model for which value changes should be audited"
        # The use of _meta is not encouraged, as it is not an external API for Django
        # But I don't see any other reliable way to get a list of a model's fields.
        return [f.column for f in self._meta.fields if f.name not in self.audit_ignore]
        
