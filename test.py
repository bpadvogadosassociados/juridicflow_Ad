#!/usr/bin/env python
"""
Script para testar API do JuridicFlow
Uso: python test_api.py
"""

import requests
import json
from datetime import datetime, timedelta

# Configuração
BASE_URL = "http://localhost:8000/api"
LOGIN_EMAIL = "teste@gmail.com"  # ✅ TROCAR PELO SEU EMAIL
LOGIN_PASSWORD = "tetete123"           # ✅ TROCAR PELA SUA SENHA

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

class APITester:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.organization = None
        self.office = None
        self.office_id = None
        
    def print_test(self, name, passed, details=""):
        status = f"{Colors.GREEN}✓ PASSOU{Colors.END}" if passed else f"{Colors.RED}✗ FALHOU{Colors.END}"
        print(f"\n{status} - {name}")
        if details:
            print(f"  {details}")
    
    def print_section(self, title):
        print(f"\n{Colors.BLUE}{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}{Colors.END}")
    
    def test_login(self):
        """Teste 1: Login e obtenção de JWT"""
        self.print_section("TESTE 1: Autenticação JWT")
        
        url = f"{BASE_URL}/auth/login/"
        payload = {
            "email": LOGIN_EMAIL,
            "password": LOGIN_PASSWORD
        }
        
        print(f"POST {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, json=payload)
            data = response.json()
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if response.status_code == 200 and "access" in data:
                self.access_token = data["access"]
                self.refresh_token = data.get("refresh")
                self.print_test("Login", True, f"Token obtido: {self.access_token[:20]}...")
                return True
            else:
                self.print_test("Login", False, f"Erro: {data}")
                return False
                
        except Exception as e:
            self.print_test("Login", False, f"Exceção: {str(e)}")
            return False
    
    def test_me(self):
        """Teste 2: Endpoint /auth/me/"""
        self.print_section("TESTE 2: Dados do Usuário (/auth/me/)")
        
        url = f"{BASE_URL}/auth/me/"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        print(f"GET {url}")
        
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if response.status_code == 200 and "email" in data:
                self.print_test("GET /auth/me/", True, f"Email: {data['email']}")
                return True
            else:
                self.print_test("GET /auth/me/", False, f"Erro: {data}")
                return False
                
        except Exception as e:
            self.print_test("GET /auth/me/", False, f"Exceção: {str(e)}")
            return False
    
    def test_memberships(self):
        """Teste 3: Listar memberships"""
        self.print_section("TESTE 3: Memberships (/auth/memberships/)")
        
        url = f"{BASE_URL}/auth/memberships/"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        print(f"GET {url}")
        
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if response.status_code == 200 and isinstance(data, list) and len(data) > 0:
                self.organization = data[0].get("organization")
                self.office = data[0].get("office")
                
                if self.office:
                    self.office_id = self.office.get("id")
                
                self.print_test(
                    "GET /auth/memberships/", 
                    True, 
                    f"Org: {self.organization.get('name') if self.organization else 'N/A'}, "
                    f"Office ID: {self.office_id or 'N/A'}"
                )
                return True
            else:
                self.print_test("GET /auth/memberships/", False, "Sem memberships")
                return False
                
        except Exception as e:
            self.print_test("GET /auth/memberships/", False, f"Exceção: {str(e)}")
            return False
    
    def test_offices(self):
        """Teste 4: Listar offices"""
        self.print_section("TESTE 4: Offices (/org/offices/)")
        
        url = f"{BASE_URL}/org/offices/"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        print(f"GET {url}")
        
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if response.status_code == 200:
                self.print_test("GET /org/offices/", True, f"Total: {len(data)} offices")
                
                if len(data) > 0 and not self.office_id:
                    self.office_id = data[0]["id"]
                    print(f"  {Colors.YELLOW}Office ID definido: {self.office_id}{Colors.END}")
                
                return True
            else:
                self.print_test("GET /org/offices/", False, f"Erro: {data}")
                return False
                
        except Exception as e:
            self.print_test("GET /org/offices/", False, f"Exceção: {str(e)}")
            return False
    
    def test_customers_list(self):
        """Teste 5: Listar customers"""
        self.print_section("TESTE 5: Customers - Listar (/customers/)")
        
        if not self.office_id:
            self.print_test("GET /customers/", False, "Office ID não definido")
            return False
        
        url = f"{BASE_URL}/customers/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Office-Id": str(self.office_id)
        }
        
        print(f"GET {url}")
        print(f"Headers: X-Office-Id: {self.office_id}")
        
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)[:500]}...")
            
            if response.status_code == 200:
                results = data.get("results", data) if isinstance(data, dict) else data
                self.print_test("GET /customers/", True, f"Total: {len(results)} customers")
                return True
            else:
                self.print_test("GET /customers/", False, f"Erro: {data}")
                return False
                
        except Exception as e:
            self.print_test("GET /customers/", False, f"Exceção: {str(e)}")
            return False
    
    def test_processes_list(self):
        """Teste 6: Listar processos"""
        self.print_section("TESTE 6: Processos - Listar (/processes/)")
        
        if not self.office_id:
            self.print_test("GET /processes/", False, "Office ID não definido")
            return False
        
        url = f"{BASE_URL}/processes/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Office-Id": str(self.office_id)
        }
        
        print(f"GET {url}")
        
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)[:500]}...")
            
            if response.status_code == 200:
                results = data.get("results", data) if isinstance(data, dict) else data
                self.print_test("GET /processes/", True, f"Total: {len(results)} processos")
                
                # Mostra primeiro processo se existir
                if len(results) > 0:
                    first = results[0]
                    print(f"  Primeiro processo: {first.get('number')} - {first.get('subject', 'Sem assunto')}")
                    print(f"  Prazos: {first.get('deadlines_count', 0)}")
                
                return True
            else:
                self.print_test("GET /processes/", False, f"Erro: {data}")
                return False
                
        except Exception as e:
            self.print_test("GET /processes/", False, f"Exceção: {str(e)}")
            return False
    
    def test_processes_create(self):
        """Teste 7: Criar processo"""
        self.print_section("TESTE 7: Processos - Criar (POST /processes/)")
        
        if not self.office_id:
            self.print_test("POST /processes/", False, "Office ID não definido")
            return False
        
        url = f"{BASE_URL}/processes/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Office-Id": str(self.office_id),
            "Content-Type": "application/json"
        }
        
        # Gera número CNJ teste
        year = datetime.now().year
        number = f"0000001-00.{year}.8.26.0100"
        
        payload = {
            "number": number,
            "court": "TJSP - Teste API",
            "subject": f"Processo teste criado via API - {datetime.now()}",
            "phase": "initial",
            "status": "active"
        }
        
        print(f"POST {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if response.status_code == 201:
                self.print_test("POST /processes/", True, f"Processo criado: {data.get('number')}")
                return data.get("id")
            else:
                self.print_test("POST /processes/", False, f"Erro: {data}")
                return False
                
        except Exception as e:
            self.print_test("POST /processes/", False, f"Exceção: {str(e)}")
            return False
    
    def test_deadlines_list(self):
        """Teste 8: Listar prazos"""
        self.print_section("TESTE 8: Prazos - Listar (/deadlines/)")
        
        if not self.office_id:
            self.print_test("GET /deadlines/", False, "Office ID não definido")
            return False
        
        url = f"{BASE_URL}/deadlines/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Office-Id": str(self.office_id)
        }
        
        print(f"GET {url}")
        
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)[:500]}...")
            
            if response.status_code == 200:
                results = data.get("results", data) if isinstance(data, dict) else data
                self.print_test("GET /deadlines/", True, f"Total: {len(results)} prazos")
                
                # Mostra primeiro prazo se existir
                if len(results) > 0:
                    first = results[0]
                    print(f"  Primeiro prazo: {first.get('title')}")
                    print(f"  Data: {first.get('due_date')}")
                    if first.get('related_process'):
                        print(f"  Processo: {first['related_process'].get('number')}")
                
                return True
            else:
                self.print_test("GET /deadlines/", False, f"Erro: {data}")
                return False
                
        except Exception as e:
            self.print_test("GET /deadlines/", False, f"Exceção: {str(e)}")
            return False
    
    def test_deadlines_create(self):
        """Teste 9: Criar prazo"""
        self.print_section("TESTE 9: Prazos - Criar (POST /deadlines/)")
        
        if not self.office_id:
            self.print_test("POST /deadlines/", False, "Office ID não definido")
            return False
        
        url = f"{BASE_URL}/deadlines/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Office-Id": str(self.office_id),
            "Content-Type": "application/json"
        }
        
        due_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        
        payload = {
            "title": f"Prazo teste API - {datetime.now()}",
            "due_date": due_date,
            "type": "legal",
            "priority": "high",
            "description": "Prazo criado via script de teste da API"
        }
        
        print(f"POST {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if response.status_code == 201:
                self.print_test("POST /deadlines/", True, f"Prazo criado: {data.get('title')}")
                return True
            else:
                self.print_test("POST /deadlines/", False, f"Erro: {data}")
                return False
                
        except Exception as e:
            self.print_test("POST /deadlines/", False, f"Exceção: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Executa todos os testes em sequência"""
        print(f"\n{Colors.BLUE}{'='*60}")
        print(f"  🧪 TESTADOR DA API JURIDICFLOW")
        print(f"  Base URL: {BASE_URL}")
        print(f"  Email: {LOGIN_EMAIL}")
        print(f"{'='*60}{Colors.END}\n")
        
        tests = [
            ("Login", self.test_login),
            ("User Info", self.test_me),
            ("Memberships", self.test_memberships),
            ("Offices", self.test_offices),
            ("Customers List", self.test_customers_list),
            ("Processes List", self.test_processes_list),
            ("Processes Create", self.test_processes_create),
            ("Deadlines List", self.test_deadlines_list),
            ("Deadlines Create", self.test_deadlines_create),
        ]
        
        passed = 0
        failed = 0
        
        for name, test_func in tests:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
        
        # Resumo
        print(f"\n{Colors.BLUE}{'='*60}")
        print(f"  📊 RESUMO DOS TESTES")
        print(f"{'='*60}{Colors.END}")
        print(f"{Colors.GREEN}✓ Passaram: {passed}{Colors.END}")
        print(f"{Colors.RED}✗ Falharam: {failed}{Colors.END}")
        print(f"Total: {passed + failed}")
        
        if failed == 0:
            print(f"\n{Colors.GREEN}🎉 Todos os testes passaram!{Colors.END}\n")
        else:
            print(f"\n{Colors.YELLOW}⚠️  Alguns testes falharam. Verifique os erros acima.{Colors.END}\n")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("INSTRUÇÕES:")
    print("="*60)
    print("1. Edite LOGIN_EMAIL e LOGIN_PASSWORD no topo do arquivo")
    print("2. Certifique-se que o servidor está rodando: python manage.py runserver")
    print("3. Execute: python test_api.py")
    print("="*60 + "\n")
    
    if LOGIN_EMAIL == "seu_email@exemplo.com":
        print(f"{Colors.RED}❌ ERRO: Edite LOGIN_EMAIL e LOGIN_PASSWORD antes de executar!{Colors.END}\n")
    else:
        tester = APITester()
        tester.run_all_tests()