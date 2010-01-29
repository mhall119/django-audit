"""
Hook existing objects into auditing sytem through Django signals

Use:

from audit.signals import auditSave, auditDelete
from django.db.models.signals import pre_save, pre_delete

pre_save.connect(auditSave, sender=YourObject)
pre_delete.connect(auditDelete, sender=YourObject)

"""
import audituser
from models import AuditRecord

def auditSave(sender, **kwargs):
    if (isinstance(sender, models.AuditModel) or isinstance(sender, models.AuditRecord)):
        return# AuditModel objects will handle this themselves
    
    instance = kwargs['instance']
    if (instance.pk is not None and instance.pk > 0):
        try:
            old = instance.__class__.objects.get(id=instance.pk)
        except:
            old = instance.__class__()
    else:
        old = instance.__class__()
        
    for f in _get_audit_fields(instance):
        oldval = getattr(old, f)
        newval = getattr(instance, f)

        if (isinstance(oldval, django.db.models.Model)):
            oldval = getattr(oldval, 'pk', oldval)
        if (isinstance(newval, django.db.models.Model)):
            newval = getattr(newval, 'pk', newval)

        if (oldval != newval):
            _recordChange(instance, f, oldval, newval)
    
def auditDelete(sender, **kwargs):
    if (isinstance(sender, models.AuditModel) or isinstance(sender, models.AuditRecord)):
        return# AuditModels object will handle this themselves
    
    instance = kwargs['instance']
    if (instance.pk is not None and instance.pk > 0):
        old = instance.__class__.objects.get(id=instance.pk)
        for f in _get_audit_fields(instance):
            _recordChange(instance, f, getattr(old, f), None)
   
def _recordChange(instance, fieldname, oldval, newval):
    rec = AuditRecord()
    rec.user_id = audituser.get_current_user_id()
    rec.app_name = instance._meta.app_label;
    rec.model_name = instance.__class__.__name__
    rec.model_id = instance.id
    rec.field_name = fieldname
    rec.old_val = oldval
    rec.new_val = newval
    rec.save()

def _recordChange_old(instance, fieldname, oldval, newval):
    "Record a modified field in the audit table"
    from django.db import connection, transaction
    cursor = connection.cursor()

    query = "INSERT INTO auditlog (audit_date, audit_user, model_name, model_id, field_name, old_value, new_value) values (null, %s, %s, %s, %s, %s, %s)"
    cursor.execute(query, [audituser.get_current_user_id(), instance.__class__.__name__, instance.id, fieldname, oldval, newval])
    transaction.commit_unless_managed()
    
def _get_audit_fields(instance):
    "Get a list of fields from a model for which value changes should be audited"
    # The use of _meta is not encouraged, as it is not an external API for Django
    # But I don't see any other reliable way to get a list of a model's fields.
    return [f.column for f in self._meta.fields]
