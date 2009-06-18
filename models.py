from django.db import models
import audituser

class AuditRecord(models.Model):
    audit_date = models.DateTimeField(auto_now_add=True)
    user_id = models.PositiveIntegerField()
    app_name = models.CharField(max_length = 50)
    model_name = models.CharField(max_length = 50)
    model_id = models.PositiveIntegerField()
    field_name = models.CharField(max_length = 50)
    old_val = models.CharField(max_length = 255)
    new_val = models.CharField(max_length = 255)

    class Meta:
        ordering = ['audit_date']
        db_table = 'audit_log'
        
    def __unicode__(self):
        return "%s.%s[%s].%s: %s -> %s" % (self.app_name, self.model_name, self.model_id, self.field_name, self.old_val, self.new_val)
    
class AuditModel(models.Model):
    "Base Model that offer automatic Auditing on calls to save() and disabled delete()"
    
    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False):
        # add auditing functionality when a sub-class is saved
        
        # Get the currently saved value for the model
        # Create a new model of the same class if no previous instance exist
        if (self.pk is not None and self.pk > 0):
            try:
                old = self.__class__.objects.get(id=self.pk)
            except:
                old = self.__class__()
        else:
            old = self.__class__()
            
        # model is saved prior to auditing, to ensure that we don't 
        # record a change before it is made
        super(AuditModel, self).save(force_insert, force_update)

        for f in self._get_audit_fields():
            oldval = getattr(old, f)
            newval = getattr(self, f)
            if (oldval != newval):
                self._recordChange(f, oldval, newval)
        
    def delete(self):
        if (self.pk is not None and self.pk > 0):
            old = self.__class__.objects.get(id=self.pk)
            for f in old._get_audit_fields():
                self._recordChange(f, getattr(old, f), None)
        super(AuditModel, self).delete()
    
    def auditLog(self):
        return AuditRecord.objects.filter(app_name=self._meta.app_label, model_name=self.__class__.__name__, model_id=self.id)

    def _recordChange(self, fieldname, oldval, newval):
        rec = AuditRecord()
        rec.user_id = audituser.get_current_user_id()
        rec.app_name = self._meta.app_label;
        rec.model_name = self.__class__.__name__
        rec.model_id = self.id
        rec.field_name = fieldname
        rec.old_val = oldval
        rec.new_val = newval
        rec.save()
        
    def _recordChange_old(self, fieldname, oldval, newval):
        "Record a modified field in the audit table"
        from django.db import connection, transaction
        cursor = connection.cursor()
    
        query = "INSERT INTO auditlog (audit_date, audit_user, model_name, model_id, field_name, old_value, new_value) values (null, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, [audituser.get_current_user_id(), self.__class__.__name__, self.id, fieldname, oldval, newval])
        transaction.commit_unless_managed()
        
    def _get_audit_fields(self):
        "Get a list of fields from a model for which value changes should be audited"
        # The use of _meta is not encouraged, as it is not an external API for Django
        # But I don't see any other reliable way to get a list of a model's fields.
        return [f.name for f in self._meta.local_fields]
        
