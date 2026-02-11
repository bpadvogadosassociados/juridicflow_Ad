"""
Management command: migra tags CSV → model Tag M2M.

Uso:
    python manage.py migrate_tags_to_m2m

Pré-requisitos:
    1. Model Tag criado em apps.core.models
    2. Campo M2M adicionado em Customer e Document:
        tag_objects = models.ManyToManyField("core.Tag", blank=True, related_name="...")
    3. Migrations rodadas

Este command é idempotente — pode ser executado múltiplas vezes.
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.core.models import Tag
from apps.customers.models import Customer
from apps.documents.models import Document


class Command(BaseCommand):
    help = "Migra tags CSV (campo 'tags') para M2M com model Tag"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula sem salvar",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN — nada será salvo"))

        total_tags_created = 0
        total_links = 0

        # ---------- CUSTOMERS ----------
        self.stdout.write("\n📋 Migrando tags de Customer...")
        customers = Customer.objects.exclude(tags="").select_related("organization")

        for customer in customers:
            org = customer.organization
            raw_tags = [t.strip() for t in customer.tags.split(",") if t.strip()]

            for tag_text in raw_tags:
                slug = slugify(tag_text)
                if not slug:
                    continue

                if not dry_run:
                    tag, created = Tag.objects.get_or_create(
                        organization=org,
                        slug=slug,
                        defaults={"name": tag_text},
                    )
                    if created:
                        total_tags_created += 1

                    if hasattr(customer, "tag_objects"):
                        customer.tag_objects.add(tag)
                        total_links += 1
                else:
                    self.stdout.write(f"  Customer #{customer.id}: '{tag_text}' → slug='{slug}'")

        # ---------- DOCUMENTS ----------
        self.stdout.write("\n📄 Migrando tags de Document...")
        documents = Document.objects.exclude(tags="").select_related("organization")

        for doc in documents:
            org = doc.organization
            raw_tags = [t.strip() for t in doc.tags.split(",") if t.strip()]

            for tag_text in raw_tags:
                slug = slugify(tag_text)
                if not slug:
                    continue

                if not dry_run:
                    tag, created = Tag.objects.get_or_create(
                        organization=org,
                        slug=slug,
                        defaults={"name": tag_text},
                    )
                    if created:
                        total_tags_created += 1

                    if hasattr(doc, "tag_objects"):
                        doc.tag_objects.add(tag)
                        total_links += 1
                else:
                    self.stdout.write(f"  Document #{doc.id}: '{tag_text}' → slug='{slug}'")

        # ---------- RESULTADO ----------
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("Nenhuma alteração feita (dry run)."))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"✅ Migração concluída: {total_tags_created} tags criadas, {total_links} vínculos M2M."
            ))
            self.stdout.write(self.style.NOTICE(
                "⚠️  O campo CSV 'tags' pode ser removido em uma migration futura "
                "após validar que todos os dados foram migrados."
            ))