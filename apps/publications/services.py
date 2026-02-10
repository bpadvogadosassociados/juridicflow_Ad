"""
SERVICES - LÓGICA DE NEGÓCIO SEPARADA
Seguindo orientação do gerente: serviços isolados e testáveis
"""

import re
from datetime import timedelta
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType


class CNJMatcher:
    """Detecta e valida números CNJ em texto"""
    
    CNJ_PATTERN = r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}'
    
    @classmethod
    def extract_cnj(cls, text):
        """Extrai números CNJ do texto"""
        matches = re.findall(cls.CNJ_PATTERN, text)
        return list(set(matches))  # Remove duplicados
    
    @classmethod
    def find_process(cls, cnj_number, office, organization=None):
        """
        Busca processo pelo número CNJ dentro do tenant correto.
        Inclui filtro por organization além de office para evitar
        cross-tenant lookup. Respeita soft-delete se o model suportar.
        """
        from apps.processes.models import Process
        try:
            qs = Process.objects.filter(number=cnj_number, office=office)
            if organization is not None:
                qs = qs.filter(organization=organization)
            # Respeita soft-delete caso o model herde SoftDeleteModel
            if hasattr(Process, 'is_deleted'):
                qs = qs.filter(is_deleted=False)
            return qs.get()
        except Process.DoesNotExist:
            return None
        except Process.MultipleObjectsReturned:
            # Não deve acontecer (unique_together), mas registra e retorna o primeiro
            import logging
            logging.getLogger(__name__).warning(
                "Múltiplos processos com CNJ %s no office %s", cnj_number, office
            )
            return qs.first()


class DeadlineBuilder:
    """Cria prazos baseados em regras configuradas"""
    
    @classmethod
    def build_from_event(cls, judicial_event):
        """
        Cria Deadline a partir de JudicialEvent
        Usa PublicationRule para calcular prazo
        """
        from apps.publications.models import PublicationRule
        from apps.deadlines.models import Deadline
        
        # Busca regra ativa para o tipo de evento
        rule = PublicationRule.objects.filter(
            organization=judicial_event.organization,
            office=judicial_event.office,
            event_type=judicial_event.event_type,
            is_active=True
        ).order_by('-priority').first()
        
        if not rule or not rule.auto_create_deadline:
            return None
        
        # Calcula data de vencimento
        base_date = judicial_event.publication.publication_date
        due_date = cls._calculate_due_date(base_date, rule.days, rule.business_days)
        
        # Cria o prazo
        deadline = Deadline.objects.create(
            organization=judicial_event.organization,
            office=judicial_event.office,
            title=f"{judicial_event.get_event_type_display()} - {judicial_event.publication.process_cnj or 'Sem CNJ'}",
            due_date=due_date,
            type="legal",
            priority=cls._map_urgency_to_priority(judicial_event.urgency),
            description=f"Prazo derivado de publicação: {judicial_event.publication.text_preview}",
            responsible=judicial_event.assigned_to,
        )
        
        # Vincula ao processo se existir
        if judicial_event.process:
            ct = ContentType.objects.get_for_model(judicial_event.process.__class__)
            deadline.content_type = ct
            deadline.object_id = judicial_event.process.id
            deadline.save()
        
        return deadline
    
    @staticmethod
    def _calculate_due_date(base_date, days, business_days=True):
        """Calcula data de vencimento (dias úteis ou corridos)"""
        if not business_days:
            return base_date + timedelta(days=days)
        
        # Cálculo simplificado de dias úteis (MVP)
        # TODO V2: Usar biblioteca de feriados brasileiros
        current_date = base_date
        days_counted = 0
        
        while days_counted < days:
            current_date += timedelta(days=1)
            # Ignora sábado (5) e domingo (6)
            if current_date.weekday() < 5:
                days_counted += 1
        
        return current_date
    
    @staticmethod
    def _map_urgency_to_priority(urgency):
        """Mapeia urgência para prioridade do Deadline"""
        mapping = {
            "critical": "urgent",
            "urgent": "high",
            "normal": "medium",
        }
        return mapping.get(urgency, "medium")


class UrgencyCalculator:
    """Calcula urgência baseado no prazo"""
    
    @staticmethod
    def calculate(due_date):
        """Retorna urgência baseado em dias até vencimento"""
        if not due_date:
            return "normal"
        
        today = timezone.now().date()
        delta = (due_date - today).days
        
        if delta < 0:
            return "critical"  # Vencido
        elif delta <= 3:
            return "critical"  # Menos de 3 dias
        elif delta <= 7:
            return "urgent"    # 3-7 dias
        else:
            return "normal"    # Mais de 7 dias


class TextParser:
    """Parser de texto de publicações (MVP simplificado)"""
    
    @staticmethod
    def extract_metadata(raw_text):
        """
        Extrai metadados básicos do texto
        MVP: CNJ, palavras-chave simples
        V2: NER, ML, etc
        """
        metadata = {}
        
        # Extrai CNJs
        cnjs = CNJMatcher.extract_cnj(raw_text)
        if cnjs:
            metadata['cnj_numbers'] = cnjs
            metadata['main_cnj'] = cnjs[0]  # Primeiro CNJ encontrado
        
        # Detecta tipo (heurística simples)
        text_lower = raw_text.lower()
        
        if 'citação' in text_lower or 'citar' in text_lower:
            metadata['suggested_type'] = 'citacao'
        elif 'intimação' in text_lower or 'intimar' in text_lower:
            metadata['suggested_type'] = 'intimacao'
        elif 'sentença' in text_lower:
            metadata['suggested_type'] = 'sentenca'
        elif 'acórdão' in text_lower or 'acordão' in text_lower:
            metadata['suggested_type'] = 'acordao'
        elif 'decisão' in text_lower:
            metadata['suggested_type'] = 'decisao'
        elif 'despacho' in text_lower:
            metadata['suggested_type'] = 'despacho'
        else:
            metadata['suggested_type'] = 'other'
        
        return metadata
    
    @staticmethod
    def matches_filters(raw_text, filters):
        """
        Verifica se texto bate com algum filtro.
        Matching primário: CNJ
        Matching secundário: OAB, CNPJ, CPF (ignora formatação)
        Terciário: Keywords (auxiliar)

        `filters` pode ser QuerySet ou lista de PublicationFilter.
        case_sensitive é avaliado por filtro, individualmente.
        """
        # Extrai CNJs uma única vez para reuso
        cnjs_no_text = CNJMatcher.extract_cnj(raw_text)
        # Versão lowercased do texto para comparações insensíveis
        raw_text_lower = raw_text.lower()
        # Versão sem pontuação para documentos (OAB/CPF/CNPJ)
        raw_text_digits = re.sub(r'\D', '', raw_text)

        for f in filters:
            # Decide se compara com o texto original ou lowercased
            text_to_search = raw_text if f.case_sensitive else raw_text_lower
            value = f.value if f.case_sensitive else f.value.lower()

            if f.filter_type == 'cnj':
                # Match exato: CNJ detectado deve estar na lista
                if f.value in cnjs_no_text:
                    return True, f

            elif f.filter_type in ('oab', 'cpf', 'cnpj'):
                # Remove formatação de ambos antes de comparar
                clean_value = re.sub(r'\D', '', f.value)
                if clean_value and clean_value in raw_text_digits:
                    return True, f

            elif f.filter_type == 'keyword':
                # Match simples de substring
                if value in text_to_search:
                    return True, f

        return False, None


class PublicationProcessor:
    """Processa publicação: cria evento, prazo, vincula processo"""
    
    @classmethod
    def process(cls, publication, auto_create_event=True):
        """
        Processa uma publicação recém-importada.

        Ordem correta:
        1. Extrai metadados do texto
        2. Detecta e persiste CNJ na publication
        3. Detecta processo vinculado
        4. Resolve responsável ANTES de criar deadline
        5. Cria JudicialEvent já com assigned_to preenchido
        6. Cria Deadline com responsible já conhecido
        7. Recalcula urgência com base no prazo obtido
        """
        from apps.publications.models import JudicialEvent

        # 1. Extrai metadados
        metadata = TextParser.extract_metadata(publication.raw_text)
        publication.metadata = metadata
        publication.save()

        # 2. Detecta e persiste CNJ
        process = None
        if metadata.get('main_cnj'):
            publication.process_cnj = metadata['main_cnj']
            publication.save()
            # 3. Busca processo
            process = CNJMatcher.find_process(
                metadata['main_cnj'],
                publication.office,
                publication.organization,
            )

        if not auto_create_event:
            return None

        # 4. Resolve responsável ANTES de criar qualquer objeto de deadline
        responsible = None
        assigned_at = None
        if process and hasattr(process, 'responsible') and process.responsible_id:
            responsible = process.responsible
            assigned_at = timezone.now()

        # 5. Cria JudicialEvent já com responsável
        event = JudicialEvent.objects.create(
            organization=publication.organization,
            office=publication.office,
            publication=publication,
            event_type=metadata.get('suggested_type', 'other'),
            process=process,
            assigned_to=responsible,
            assigned_at=assigned_at,
            status='assigned' if responsible else 'new',
        )

        # 6. Cria Deadline (agora sabe o responsável)
        deadline = DeadlineBuilder.build_from_event(event)
        if deadline:
            # Garante que deadline também tem o responsável
            if responsible and not deadline.responsible_id:
                deadline.responsible = responsible
                deadline.save(update_fields=['responsible'])

            # 7. Recalcula urgência com base no prazo real
            event.deadline = deadline
            event.urgency = UrgencyCalculator.calculate(deadline.due_date)
            event.save(update_fields=['deadline', 'urgency'])

        return event