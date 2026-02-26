"""
SERVICES — lógica de negócio isolada e testável.

Providers de integração:
  - DataJudProvider   → API pública do CNJ (Elasticsearch)
  - ComunicaProvider  → Download de cadernos PJe (ZIP + JSON)
  - DjenProvider      → Diário Eletrônico Nacional

Utilitários já existentes (mantidos):
  - CNJMatcher        → extrai e valida números CNJ em texto
  - TextParser        → classifica tipo de evento por heurística de texto
  - DeadlineBuilder   → cria Deadline a partir de JudicialEvent + PublicationRule
  - UrgencyCalculator → calcula urgência por dias até o prazo
  - PublicationProcessor → orquestra tudo: dado bruto → evento jurídico → prazo
"""

import re
import io
import json
import zipfile
import hashlib
import logging
from datetime import date, timedelta
from typing import Optional

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CNJMatcher — extrai e valida números CNJ em texto
# ═══════════════════════════════════════════════════════════════════════════════

class CNJMatcher:
    CNJ_PATTERN = r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}'

    @classmethod
    def extract_cnj(cls, text: str) -> list:
        return list(set(re.findall(cls.CNJ_PATTERN, text)))

    @classmethod
    def normalize(cls, number: str) -> str:
        """Remove formatação, retorna só dígitos."""
        return re.sub(r'[^0-9]', '', number)

    @classmethod
    def format(cls, number: str) -> str:
        """Dígitos → formato CNJ: NNNNNNN-DD.AAAA.J.TT.OOOO"""
        d = cls.normalize(number)
        if len(d) == 20:
            return f"{d[:7]}-{d[7:9]}.{d[9:13]}.{d[13]}.{d[14:16]}.{d[16:]}"
        return number

    @classmethod
    def extract_tribunal(cls, number: str) -> tuple[str, str]:
        """Extrai (sigla_tribunal, indice_datajud) do número CNJ."""
        d = cls.normalize(number)
        # Para qualquer inferência confiável do tribunal precisamos ao menos
        # do dígito "J" (segmento) e do "TT" (código). CNJ completo = 20 dígitos.
        if len(d) < 16:
            return "", ""
        justice = d[13]   # tipo de justiça
        code = d[14:16]   # código do tribunal
        uf_map = {
            "01": "AC", "02": "AL", "03": "AP", "04": "AM", "05": "BA",
            "06": "CE", "07": "DF", "08": "ES", "09": "GO", "10": "MA",
            "11": "MT", "12": "MS", "13": "MG", "14": "PA", "15": "PB",
            "16": "PR", "17": "PE", "18": "PI", "19": "RJ", "20": "RN",
            "21": "RS", "22": "RO", "23": "RR", "24": "SC", "25": "SE",
            "26": "SP", "27": "TO",
        }
        if justice == "8":  # TJ
            uf = uf_map.get(code, code)
            sigla = f"TJ{uf}"
            return sigla, sigla.lower()
        elif justice == "4":  # TRF
            return f"TRF{int(code)}", f"trf{int(code)}"
        elif justice == "5":  # TRT
            return f"TRT{int(code)}", f"trt{int(code)}"
        elif justice == "1":
            return "STF", "stf"
        elif justice == "3":
            return "STJ", "stj"
        elif justice == "2":
            # CNJ (Conselho Nacional de Justiça). Índice "cnj" é suportado
            # pela API pública do DataJud.
            return "CNJ", "cnj"
        return "", ""

    @classmethod
    def find_process(cls, cnj_number: str, office, organization=None):
        from apps.processes.models import Process
        try:
            qs = Process.objects.filter(number=cnj_number, office=office)
            if organization:
                qs = qs.filter(organization=organization)
            return qs.get()
        except Process.DoesNotExist:
            return None
        except Process.MultipleObjectsReturned:
            return Process.objects.filter(number=cnj_number, office=office).first()


# ═══════════════════════════════════════════════════════════════════════════════
# DataJudProvider — API pública do CNJ
# ═══════════════════════════════════════════════════════════════════════════════


class DataJudError(Exception):
    """Erro genérico do DataJud."""


class DataJudAuthError(DataJudError):
    """APIKey ausente/inválida."""


class DataJudRateLimitError(DataJudError):
    """Rate limit/limitação temporária."""


class DataJudUpstreamError(DataJudError):
    """Falha do upstream (5xx, payload inválido, etc.)."""


class DataJudProvider:
    """Integração com a API Pública do DataJud (CNJ).

    A API é baseada em Elasticsearch. Cada tribunal (e também o CNJ) expõe um
    índice próprio, por exemplo:
        https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search

    Na prática, o CNJ pode exigir APIKey mesmo para dados públicos. Este
    provider assume a presença de `settings.DATAJUD_API_KEY` (ou env var) e
    devolve erros mais explícitos quando a autenticação falha.
    """

    BASE_URL = "https://api-publica.datajud.cnj.jus.br"
    TIMEOUT = 20

    def __init__(self, api_key: str = None):
        from django.conf import settings
        import os
        self.api_key = api_key or getattr(settings, "DATAJUD_API_KEY", "") or os.getenv("DATAJUD_API_KEY", "")

        # Session com retries leves (útil contra flutuações e 429/5xx).
        self._session = requests.Session()
        try:
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            retry = Retry(
                total=3,
                backoff_factor=0.4,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(["POST", "GET"]),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
        except Exception:
            # Se urllib3/retry não estiver disponível por algum motivo,
            # seguimos com requests padrão.
            pass

    def _headers(self) -> dict:
        h = {
            "Content-Type": "application/json",
            "User-Agent": "publications-app/1.0",
        }
        if not self.api_key:
            return h

        # Formato esperado pelo CNJ: "Authorization: APIKey <chave>"
        h["Authorization"] = f"APIKey {self.api_key}"
        return h

    def search_process(self, cnj_number: str, tribunal_index: str) -> Optional[dict]:
        """
        Busca processo pelo número CNJ no índice do tribunal.
        Retorna dict normalizado ou None se não encontrado.
        """
        digits = CNJMatcher.normalize(cnj_number)
        if len(digits) != 20:
            raise ValueError("CNJ inválido: esperado 20 dígitos.")
        if not tribunal_index or not re.match(r"^[a-z0-9_]+$", tribunal_index):
            raise ValueError("Índice DataJud inválido.")
        if not self.api_key:
            raise DataJudAuthError("DATAJUD_API_KEY não configurada.")
        url = f"{self.BASE_URL}/api_publica_{tribunal_index}/_search"
        payload = {
            # numeroProcesso costuma ser keyword no índice do DataJud.
            # term evita análise e reduz falsos negativos.
            "query": {"term": {"numeroProcesso": digits}},
            "size": 1,
        }
        try:
            resp = self._session.post(url, json=payload, headers=self._headers(), timeout=self.TIMEOUT)

            if resp.status_code in (401, 403):
                raise DataJudAuthError("Não autorizado no DataJud (APIKey ausente/inválida).")
            if resp.status_code == 429:
                raise DataJudRateLimitError("DataJud limitou as requisições (429).")
            if resp.status_code == 404:
                # Índice inexistente ou endpoint não encontrado.
                return None
            if 500 <= resp.status_code <= 599:
                raise DataJudUpstreamError(f"DataJud indisponível ({resp.status_code}).")

            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            if not hits:
                return None
            return self._normalize_process(hits[0]["_source"], cnj_number, tribunal_index)
        except (DataJudError, ValueError):
            raise
        except requests.RequestException as e:
            logger.error(f"[DataJud] Falha de rede ao buscar {cnj_number}: {e}")
            raise DataJudUpstreamError("Falha de rede ao consultar o DataJud.")
        except Exception as e:
            logger.error(f"[DataJud] Erro inesperado ao buscar {cnj_number}: {e}")
            raise DataJudUpstreamError("Erro inesperado ao consultar o DataJud.")

    def _normalize_process(self, src: dict, cnj_number: str, tribunal_index: str) -> dict:
        """Normaliza a resposta do DataJud para o formato interno."""
        movimentos = src.get("movimentos", [])
        partes = src.get("partes", [])
        assuntos = src.get("assunto", [])
        classe = src.get("classe", {})

        return {
            "cnj_number": CNJMatcher.format(CNJMatcher.normalize(cnj_number)),
            "tribunal": tribunal_index.upper(),
            "tribunal_index": tribunal_index,
            "classe": classe.get("nome", ""),
            "assunto": assuntos[0].get("nome", "") if assuntos else "",
            "orgao_julgador": src.get("orgaoJulgador", {}).get("nome", ""),
            "data_ajuizamento": src.get("dataAjuizamento", "")[:10] if src.get("dataAjuizamento") else "",
            "fase_atual": movimentos[-1].get("nome", "") if movimentos else "",
            "movimentos": [
                {
                    "data": m.get("dataHora", "")[:10] if m.get("dataHora") else "",
                    "codigo": str(m.get("codigo", "")),
                    "nome": m.get("nome", ""),
                    "complemento": (m.get("complementosTabelados") or [{}])[0].get("descricao", ""),
                }
                for m in movimentos
            ],
            "partes": [
                {
                    "polo": p.get("polo", ""),
                    "nome": p.get("nome", ""),
                    "tipo": p.get("tipoPessoa", ""),
                    "advogados": [
                        a.get("nome", "") for a in (p.get("advogado") or [])
                    ],
                }
                for p in partes
            ],
        }

    def get_movements_as_publications(self, cnj_number: str, tribunal_index: str, from_date: str = None) -> list:
        """
        Retorna movimentos do processo como lista de dicts prontos para
        criar Publication (formato normalizado).
        """
        result = self.search_process(cnj_number, tribunal_index)
        if not result:
            return []

        movements = result.get("movimentos", [])
        if from_date:
            movements = [m for m in movements if m["data"] >= from_date]

        publications = []
        for m in movements:
            text = f"{m['nome']}"
            if m.get("complemento"):
                text += f" — {m['complemento']}"
            publications.append({
                "source": "datajud",
                "source_id": f"datajud_{CNJMatcher.normalize(cnj_number)}_{m['codigo']}_{m['data']}",
                "raw_text": text,
                "publication_date": m["data"] or date.today().isoformat(),
                "process_cnj": CNJMatcher.format(CNJMatcher.normalize(cnj_number)),
                "metadata": {
                    "tribunal": tribunal_index.upper(),
                    "orgao_julgador": result.get("orgao_julgador", ""),
                    "codigo_movimento": m["codigo"],
                },
            })
        return publications


# ═══════════════════════════════════════════════════════════════════════════════
# ComunicaProvider — Comunica API (PJe / Diários)
# ═══════════════════════════════════════════════════════════════════════════════

class ComunicaProvider:
    """
    Integração com a Comunica API do PJe.
    Swagger: https://comunicaapi.pje.jus.br/swagger/index.html

    Fluxo diário:
      1. Download do caderno compactado (ZIP) do dia
      2. Parse do ZIP → lista de comunicações JSON
      3. Matching contra ProcessMonitoring e PublicationFilter ativos
      4. Criação de Publication para cada comunicação relevante
    """

    BASE_URL = "https://comunicaapi.pje.jus.br/api/v1"
    TIMEOUT = 120  # ZIPs podem ser grandes

    def __init__(self, token: str = None):
        from django.conf import settings
        self.token = token or getattr(settings, "COMUNICA_API_TOKEN", "")

    def _headers(self) -> dict:
        h = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def check_process(self, cnj_number: str) -> Optional[dict]:
        """
        Verifica se um processo existe na Comunica API.
        Retorna a comunicação mais recente ou None.
        GET /api/v1/comunicacao?numeroProcesso=...
        """
        digits = CNJMatcher.normalize(cnj_number)
        try:
            resp = requests.get(
                f"{self.BASE_URL}/comunicacao",
                params={"numeroProcesso": digits, "pagina": 1, "itensPorPagina": 1},
                headers=self._headers(),
                timeout=15,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            items = data if isinstance(data, list) else data.get("items", data.get("resultado", []))
            return items[0] if items else None
        except requests.RequestException as e:
            logger.error(f"[Comunica] Erro ao verificar {cnj_number}: {e}")
            return None

    def download_caderno(self, target_date: date) -> Optional[bytes]:
        """
        Baixa o caderno compactado do dia.
        GET /api/v1/comunicacao/download?data=YYYY-MM-DD
        Os cadernos são publicados pela manhã (geralmente 06:00–08:00).
        """
        date_str = target_date.strftime("%Y-%m-%d")
        try:
            resp = requests.get(
                f"{self.BASE_URL}/comunicacao/download",
                params={"data": date_str},
                headers=self._headers(),
                timeout=self.TIMEOUT,
                stream=True,
            )
            if resp.status_code == 404:
                logger.info(f"[Comunica] Caderno de {date_str} ainda não disponível.")
                return None
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as e:
            logger.error(f"[Comunica] Erro ao baixar caderno de {date_str}: {e}")
            return None

    def parse_caderno(self, zip_bytes: bytes, monitored_cnjs: set = None) -> list:
        """
        Extrai comunicações do ZIP e normaliza para o formato Publication.
        Se monitored_cnjs for fornecido, filtra apenas comunicações relevantes.
        """
        results = []
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                for filename in zf.namelist():
                    if not filename.lower().endswith(".json"):
                        continue
                    with zf.open(filename) as f:
                        try:
                            data = json.loads(f.read().decode("utf-8", errors="ignore"))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue
                        items = data if isinstance(data, list) else data.get("items", [])
                        for item in items:
                            pub = self._normalize_item(item)
                            if not pub:
                                continue
                            cnj_digits = CNJMatcher.normalize(pub["process_cnj"])
                            if monitored_cnjs and cnj_digits not in monitored_cnjs:
                                continue
                            results.append(pub)
        except zipfile.BadZipFile:
            logger.error("[Comunica] ZIP inválido recebido.")
        except Exception as e:
            logger.error(f"[Comunica] Erro ao parsear caderno: {e}")
        return results

    def _normalize_item(self, item: dict) -> Optional[dict]:
        cnj_raw = item.get("numeroProcesso", "")
        if not cnj_raw:
            return None
        cnj_digits = CNJMatcher.normalize(cnj_raw)
        pub_date = (item.get("dataDisponibilizacao") or "")[:10] or date.today().isoformat()
        tipo = item.get("tipoComunicacao", "Comunicação")
        orgao = item.get("nomeOrgaoJulgador", "")
        texto = item.get("textoPublicacao", "")

        return {
            "source": "comunica",
            "source_id": (
                item.get("id") or
                item.get("idComunicacao") or
                f"comunica_{cnj_digits}_{pub_date}"
            ),
            "raw_text": texto or f"{tipo} — {orgao}",
            "publication_date": pub_date,
            "process_cnj": CNJMatcher.format(cnj_digits),
            "metadata": {
                "tipo_comunicacao": tipo,
                "sigla_tipo": item.get("siglaTipoComunicacao", ""),
                "orgao_julgador": orgao,
                "url_publicacao": item.get("urlPublicacao", ""),
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TextParser — classifica o tipo de evento por heurística
# ═══════════════════════════════════════════════════════════════════════════════

class TextParser:
    KEYWORD_MAP = [
        (["citação", "citar", "citado", "citada"], "citacao"),
        (["intimação", "intimar", "intimado", "intimada"], "intimacao"),
        (["sentença", "sentenç"], "sentenca"),
        (["acórdão", "acordão"], "acordao"),
        (["decisão interlocutória", "decisão"], "decisao"),
        (["despacho"], "despacho"),
        (["juntada", "juntou", "documento juntado"], "juntada"),
        (["audiência", "audiencia"], "audiencia"),
        (["petição", "peticao", "petição inicial"], "peticao"),
        (["edital"], "edital"),
    ]

    @classmethod
    def classify_event_type(cls, text: str) -> str:
        lower = text.lower()
        for keywords, event_type in cls.KEYWORD_MAP:
            if any(k in lower for k in keywords):
                return event_type
        return "movimento"

    @classmethod
    def extract_metadata(cls, raw_text: str) -> dict:
        metadata = {}
        cnjs = CNJMatcher.extract_cnj(raw_text)
        if cnjs:
            metadata["cnj_numbers"] = cnjs
            metadata["main_cnj"] = cnjs[0]
        metadata["suggested_type"] = cls.classify_event_type(raw_text)
        return metadata

    @classmethod
    def matches_filters(cls, raw_text: str, filters) -> tuple:
        cnjs_in_text = CNJMatcher.extract_cnj(raw_text)
        raw_lower = raw_text.lower()
        raw_digits = re.sub(r'\D', '', raw_text)

        for f in filters:
            text_to_search = raw_text if f.case_sensitive else raw_lower
            value = f.value if f.case_sensitive else f.value.lower()

            if f.filter_type == "cnj":
                if f.value in cnjs_in_text:
                    return True, f
            elif f.filter_type in ("oab", "cpf", "cnpj"):
                clean = re.sub(r'\D', '', f.value)
                if clean and clean in raw_digits:
                    return True, f
            elif f.filter_type == "keyword":
                if value in text_to_search:
                    return True, f
        return False, None


# ═══════════════════════════════════════════════════════════════════════════════
# UrgencyCalculator
# ═══════════════════════════════════════════════════════════════════════════════

class UrgencyCalculator:
    @staticmethod
    def calculate(due_date) -> str:
        if not due_date:
            return "normal"
        delta = (due_date - timezone.now().date()).days
        if delta < 0:
            return "critical"
        elif delta <= 3:
            return "critical"
        elif delta <= 7:
            return "urgent"
        return "normal"


# ═══════════════════════════════════════════════════════════════════════════════
# DeadlineBuilder
# ═══════════════════════════════════════════════════════════════════════════════

class DeadlineBuilder:
    @classmethod
    def build_from_event(cls, judicial_event):
        from apps.publications.models import PublicationRule
        from apps.deadlines.models import Deadline

        rule = PublicationRule.objects.filter(
            organization=judicial_event.organization,
            office=judicial_event.office,
            event_type=judicial_event.event_type,
            is_active=True,
        ).order_by("-priority").first()

        if not rule or not rule.auto_create_deadline:
            return None

        base_date = judicial_event.publication.publication_date
        due_date = cls._calc_due_date(base_date, rule.days, rule.business_days)

        deadline = Deadline.objects.create(
            organization=judicial_event.organization,
            office=judicial_event.office,
            title=(
                f"{judicial_event.get_event_type_display()} — "
                f"{judicial_event.publication.process_cnj or 'Sem CNJ'}"
            ),
            due_date=due_date,
            type="legal",
            priority=cls._urgency_to_priority(judicial_event.urgency),
            description=f"Prazo derivado de publicação: {judicial_event.publication.text_preview}",
            responsible=judicial_event.assigned_to,
        )
        return deadline

    @staticmethod
    def _calc_due_date(base_date, days: int, business_days: bool) -> date:
        if not business_days:
            return base_date + timedelta(days=days)
        current = base_date
        counted = 0
        while counted < days:
            current += timedelta(days=1)
            if current.weekday() < 5:  # seg–sex
                counted += 1
        return current

    @staticmethod
    def _urgency_to_priority(urgency: str) -> str:
        return {"critical": "urgent", "urgent": "high", "normal": "medium"}.get(urgency, "medium")


# ═══════════════════════════════════════════════════════════════════════════════
# PublicationProcessor — orquestra tudo
# ═══════════════════════════════════════════════════════════════════════════════

class PublicationProcessor:
    """
    Dado um dict de publicação normalizado (vindo de qualquer provider),
    cria Publication → JudicialEvent → Deadline, respeitando deduplicação.

    Retorna (publication, judicial_event, created: bool).
    """

    @classmethod
    def process_dict(cls, pub_dict: dict, organization, office, imported_by=None):
        """
        pub_dict deve ter os campos:
            source, source_id, raw_text, publication_date, process_cnj (opcional)
        """
        from apps.publications.models import Publication, JudicialEvent

        # 1. Deduplicação por hash
        content = f"{pub_dict['source']}:{pub_dict.get('source_id','')}:{pub_dict['raw_text']}:{pub_dict['publication_date']}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        existing = Publication.objects.filter(
            organization=organization,
            office=office,
            content_hash=content_hash,
        ).first()
        if existing:
            return existing, None, False

        # 2. Extrai metadados
        metadata = TextParser.extract_metadata(pub_dict["raw_text"])
        process_cnj = pub_dict.get("process_cnj") or metadata.get("main_cnj", "")
        extra_meta = pub_dict.get("metadata", {})

        # Normaliza publication_date para date
        pub_date = pub_dict.get("publication_date")
        if isinstance(pub_date, str):
            try:
                from datetime import datetime
                pub_date = datetime.strptime(pub_date[:10], "%Y-%m-%d").date()
            except Exception:
                # Deixa o Django tentar (ou estoura cedo se for lixo)
                pass

        # 3. Procura processo na base
        process = None
        if process_cnj:
            process = CNJMatcher.find_process(process_cnj, office, organization)

        # 4. Cria Publication
        from django.db import IntegrityError, transaction
        try:
            with transaction.atomic():
                pub = Publication.objects.create(
                    organization=organization,
                    office=office,
                    source=pub_dict["source"],
                    source_id=pub_dict.get("source_id", ""),
                    raw_text=pub_dict["raw_text"],
                    content_hash=content_hash,
                    publication_date=pub_date or pub_dict["publication_date"],
                    process_cnj=process_cnj,
                    process=process,
                    metadata={**metadata, **extra_meta},
                    imported_by=imported_by,
                )
        except IntegrityError:
            # Corrida/concorrência: alguém salvou no meio.
            existing = Publication.objects.filter(
                organization=organization,
                office=office,
                content_hash=content_hash,
            ).first()
            if existing:
                return existing, None, False
            raise

        # 5. Responsável do processo (se vinculado)
        responsible = getattr(process, "responsible", None) if process else None
        assigned_at = timezone.now() if responsible else None

        # 6. Cria JudicialEvent
        event = JudicialEvent.objects.create(
            organization=organization,
            office=office,
            publication=pub,
            event_type=metadata.get("suggested_type", "movimento"),
            process=process,
            assigned_to=responsible,
            assigned_at=assigned_at,
            status="assigned" if responsible else "new",
        )

        # 7. Cria Deadline
        deadline = DeadlineBuilder.build_from_event(event)
        if deadline:
            if responsible and not deadline.responsible_id:
                deadline.responsible = responsible
                deadline.save(update_fields=["responsible"])
            event.deadline = deadline
            event.urgency = UrgencyCalculator.calculate(deadline.due_date)
            event.save(update_fields=["deadline", "urgency"])

        return pub, event, True


# ═══════════════════════════════════════════════════════════════════════════════
# SyncService — orquestra sincronizações diárias / sob demanda
# ═══════════════════════════════════════════════════════════════════════════════

class SyncService:
    """
    Centraliza a lógica de sincronização, independente de Celery ou cron.
    Pode ser chamado via management command, Celery task, ou endpoint DRF.
    """

    @classmethod
    def sync_process_datajud(cls, monitoring, user=None) -> dict:
        """
        Sincroniza um único ProcessMonitoring via DataJud.
        Retorna stats: {'imported': int, 'skipped': int, 'errors': int}
        """
        from apps.publications.models import PublicationImport

        imp = PublicationImport.objects.create(
            organization=monitoring.organization,
            office=monitoring.office,
            source="datajud",
            reference_date=date.today(),
            status="processing",
            triggered_by=user,
            filters_applied={"cnj": monitoring.process_cnj},
        )

        stats = {"imported": 0, "skipped": 0, "errors": 0}

        try:
            tribunal_index = monitoring.tribunal_index
            if not tribunal_index:
                _, tribunal_index = CNJMatcher.extract_tribunal(monitoring.process_cnj)
                if not tribunal_index:
                    raise ValueError(f"Não foi possível detectar tribunal do CNJ: {monitoring.process_cnj}")
                monitoring.tribunal_index = tribunal_index
                monitoring.save(update_fields=["tribunal_index"])

            provider = DataJudProvider()
            from_date = None
            if monitoring.initial_sync_done:
                from_date = (monitoring.sync_cursors or {}).get("datajud")

            pub_dicts = provider.get_movements_as_publications(
                monitoring.process_cnj, tribunal_index, from_date
            )
            imp.total_found = len(pub_dicts)

            for pd in pub_dicts:
                try:
                    _, _, created = PublicationProcessor.process_dict(
                        pd, monitoring.organization, monitoring.office, user
                    )
                    if created:
                        stats["imported"] += 1
                    else:
                        stats["skipped"] += 1
                except Exception as e:
                    stats["errors"] += 1
                    imp.error_log += f"\n{e}"

            monitoring.initial_sync_done = True
            monitoring.last_synced_at = timezone.now()
            monitoring.sync_cursors = {
                **(monitoring.sync_cursors or {}),
                "datajud": date.today().isoformat(),
            }
            monitoring.save(update_fields=["initial_sync_done", "last_synced_at", "sync_cursors"])

            imp.total_imported = stats["imported"]
            imp.total_duplicates = stats["skipped"]
            imp.total_errors = stats["errors"]
            imp.status = "success" if stats["errors"] == 0 else "partial"
            imp.finished_at = timezone.now()
            imp.save()

        except Exception as e:
            stats["errors"] += 1
            imp.status = "failed"
            imp.error_log = str(e)
            imp.finished_at = timezone.now()
            imp.save()
            logger.error(f"[SyncService.datajud] Erro: {e}")

        return stats

    @classmethod
    def sync_comunica_daily(cls, organization, office, target_date: date = None, user=None) -> dict:
        """
        Baixa o caderno do dia da Comunica API e processa publicações de
        todos os processos monitorados da organização.
        """
        from apps.publications.models import ProcessMonitoring, PublicationImport

        if target_date is None:
            target_date = date.today()

        # Evita processar o mesmo dia duas vezes
        existing = PublicationImport.objects.filter(
            organization=organization,
            office=office,
            source="comunica",
            reference_date=target_date,
            status="success",
        ).exists()
        if existing:
            return {"already_done": True}

        imp = PublicationImport.objects.create(
            organization=organization,
            office=office,
            source="comunica",
            reference_date=target_date,
            status="processing",
            triggered_by=user,
        )

        stats = {"imported": 0, "skipped": 0, "errors": 0, "matched": 0}

        try:
            # CNJs monitorados e ativos
            monitorings = ProcessMonitoring.objects.filter(
                organization=organization, office=office, is_active=True,
            )
            monitored_cnjs = {
                CNJMatcher.normalize(m.process_cnj)
                for m in monitorings
                if "comunica" in (m.sources or []) or "all" in (m.sources or [])
            }

            if not monitored_cnjs:
                imp.status = "success"
                imp.summary = "Nenhum processo com monitoramento Comunica ativo."
                imp.finished_at = timezone.now()
                imp.save()
                return stats

            from django.conf import settings
            token = getattr(settings, "COMUNICA_API_TOKEN", None)
            provider = ComunicaProvider(token)

            zip_bytes = provider.download_caderno(target_date)
            if not zip_bytes:
                imp.status = "partial"
                imp.summary = f"Caderno de {target_date} não disponível."
                imp.finished_at = timezone.now()
                imp.save()
                return stats

            pub_dicts = provider.parse_caderno(zip_bytes, monitored_cnjs)
            imp.total_found = len(pub_dicts)

            for pd in pub_dicts:
                try:
                    _, event, created = PublicationProcessor.process_dict(
                        pd, organization, office, user
                    )
                    if created:
                        stats["imported"] += 1
                        if event and event.process_id:
                            stats["matched"] += 1
                    else:
                        stats["skipped"] += 1
                except Exception as e:
                    stats["errors"] += 1
                    imp.error_log += f"\n{e}"

            imp.total_imported = stats["imported"]
            imp.total_duplicates = stats["skipped"]
            imp.total_matched = stats["matched"]
            imp.total_errors = stats["errors"]
            imp.status = "success" if stats["errors"] == 0 else "partial"
            imp.summary = f"{stats['imported']} publicações importadas, {stats['matched']} vinculadas a processos."
            imp.finished_at = timezone.now()
            imp.save()

        except Exception as e:
            imp.status = "failed"
            imp.error_log = str(e)
            imp.finished_at = timezone.now()
            imp.save()
            logger.error(f"[SyncService.comunica] Erro: {e}")

        return stats

    @classmethod
    def autocomplete_process(cls, monitoring, process_data: dict):
        """
        Preenche campos do processo com dados vindos do DataJud,
        mas APENAS se autocomplete_enabled=True e o campo estiver vazio.
        """
        if not monitoring.autocomplete_enabled:
            return
        process = monitoring.process
        changed = []

        field_map = {
            "classe": ("area", None),        # approximate mapping
            "orgao_julgador": ("court", None),
        }

        if not process.title and process_data.get("classe"):
            process.title = process_data["classe"][:255]
            changed.append("title")

        if changed:
            process.save(update_fields=changed)
