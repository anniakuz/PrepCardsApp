from django.db import migrations

CREATE = """
CREATE OR REPLACE FUNCTION quiz_question_audit_fn() RETURNS trigger AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM quiz_topic WHERE id = OLD.topic_id AND owner_id IS NULL) THEN
        INSERT INTO quiz_questionaudit (question_id, action, old_text, changed_at)
        VALUES (OLD.id, TG_OP, OLD.text, now());
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER quiz_question_audit
AFTER UPDATE OR DELETE ON quiz_question
FOR EACH ROW EXECUTE FUNCTION quiz_question_audit_fn();
"""

DROP = """
DROP TRIGGER IF EXISTS quiz_question_audit ON quiz_question;
DROP FUNCTION IF EXISTS quiz_question_audit_fn();
"""


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(CREATE)


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(DROP)


class Migration(migrations.Migration):
    dependencies = [("quiz", "0001_initial")]
    operations = [migrations.RunPython(forwards, backwards)]
